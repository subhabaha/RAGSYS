"""Background processing pipeline for uploaded PDFs.

This is a plain `def` so Starlette's BackgroundTasks runs it in a threadpool
and does NOT block the event loop. The Azure SDKs used inside are synchronous
and can sleep tens of seconds on HTTP 429; running them on the loop would
freeze every request including `/health`.
"""
from __future__ import annotations

import logging
import traceback

from . import openai_service, pdf_processor, repository
from .azure_clients import get_blob_container

log = logging.getLogger(__name__)


def process_document(doc_id: str) -> None:
    try:
        doc = repository.get_document(doc_id)
        if doc is None:
            log.warning("process_document: %s not found", doc_id)
            return

        blob_name = doc["blob_name"]
        container = get_blob_container()
        blob_bytes = container.get_blob_client(blob_name).download_blob().readall()

        chunks = pdf_processor.extract_and_chunk(blob_bytes)
        if not chunks:
            doc["status"] = "failed"
            doc["error"] = "No extractable text found in PDF"
            doc["chunks_count"] = 0
            repository.update_document(doc)
            return

        texts = [c.text for c in chunks]
        try:
            embeddings = openai_service.embed_texts(texts)
        except Exception as e:
            log.exception("Embedding failed for %s", doc_id)
            doc["status"] = "failed"
            doc["error"] = f"embedding failed: {e.__class__.__name__}: {e}"
            repository.update_document(doc)
            return

        doc["chunks"] = [
            {
                "index": c.index,
                "page": c.page,
                "text": c.text,
                "embedding": emb,
            }
            for c, emb in zip(chunks, embeddings)
        ]
        doc["chunks_count"] = len(chunks)
        doc["status"] = "ready"
        doc["error"] = None
        repository.update_document(doc)
        log.info("Document %s ready with %d chunks", doc_id, len(chunks))
    except Exception as e:
        log.error("process_document crashed for %s: %s\n%s", doc_id, e, traceback.format_exc())
        try:
            doc = repository.get_document(doc_id)
            if doc is not None:
                doc["status"] = "failed"
                doc["error"] = f"{e.__class__.__name__}: {e}"
                repository.update_document(doc)
        except Exception:
            pass
