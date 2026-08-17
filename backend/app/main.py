"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import uuid

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config, processing, repository
from .azure_clients import get_blob_container, get_cosmos_container
from .models import (
    DocumentSummary,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceChunk,
    UploadResponse,
)
from .openai_service import chat_answer
from .retrieval import retrieve

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ragsys")

app = FastAPI(title="RAG Document System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Ensure Azure resources exist (idempotent) at boot.
    log.info("Verifying Azure resources...")
    get_blob_container()
    get_cosmos_container()
    log.info("Startup complete for %s", config.AZURE_STORAGE_ACCOUNT_NAME)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # Pure in-memory: must always respond fast, even while a large PDF is being
    # processed in the threadpool.
    return HealthResponse(status="ok")


@app.post("/api/upload", response_model=UploadResponse)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    doc_id = str(uuid.uuid4())
    blob_name = f"{doc_id}/{filename}"

    # Blob upload is synchronous SDK — run it off the event loop.
    import asyncio

    def _upload_blob() -> None:
        container = get_blob_container()
        container.upload_blob(name=blob_name, data=data, overwrite=True)

    await asyncio.to_thread(_upload_blob)

    await asyncio.to_thread(
        repository.create_document, doc_id, filename, blob_name, len(data)
    )

    # Starlette runs plain-def background tasks in a threadpool, keeping the
    # event loop free.
    background_tasks.add_task(processing.process_document, doc_id)

    return UploadResponse(id=doc_id, filename=filename, status="processing")


@app.get("/api/documents", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    import asyncio

    rows = await asyncio.to_thread(repository.list_documents, 500)
    # Give optional fields defaults so one malformed record cannot fail the endpoint.
    result: list[DocumentSummary] = []
    for r in rows:
        result.append(
            DocumentSummary(
                id=r.get("id", ""),
                filename=r.get("filename", ""),
                status=r.get("status", "unknown"),
                file_size=int(r.get("file_size") or 0),
                chunks_count=int(r.get("chunks_count") or 0),
                uploaded_at=r.get("uploaded_at"),
                error=r.get("error"),
            )
        )
    return result


@app.delete("/api/documents/{doc_id}")
async def delete_doc(doc_id: str):
    import asyncio

    doc = await asyncio.to_thread(repository.get_document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Not found")

    blob_name = doc.get("blob_name")

    def _delete_blob() -> None:
        if not blob_name:
            return
        try:
            get_blob_container().delete_blob(blob_name)
        except Exception:
            log.warning("Could not delete blob %s", blob_name)

    await asyncio.to_thread(_delete_blob)
    ok = await asyncio.to_thread(repository.delete_document, doc_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return {"id": doc_id, "deleted": True}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    import asyncio

    hits = await asyncio.to_thread(retrieve, req.question, req.top_k)
    if not hits:
        return QueryResponse(
            answer="No documents are available to answer this question.",
            sources=[],
        )

    context_blocks = [
        f"[{h.document_name} p.{h.page}] {h.text}" for h in hits
    ]
    answer = await asyncio.to_thread(chat_answer, req.question, context_blocks)

    sources = [
        SourceChunk(
            document_id=h.document_id,
            document_name=h.document_name,
            page=h.page,
            text=h.text,
            score=h.score,
        )
        for h in hits
    ]
    return QueryResponse(answer=answer, sources=sources)
