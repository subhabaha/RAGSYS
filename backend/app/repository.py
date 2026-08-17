"""Cosmos DB persistence for documents and chunks.

Schema (one item per document, partition key `/id`):
{
  "id": "<uuid>",
  "type": "document",
  "filename": str,
  "status": "processing" | "ready" | "failed",
  "file_size": int,
  "chunks_count": int,
  "uploaded_at": iso8601,
  "blob_name": str,
  "error": Optional[str],
  "chunks": [
     {"index": int, "page": int, "text": str, "embedding": [float, ...]}, ...
  ]
}
"""
from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional

from .azure_clients import get_cosmos_container


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def create_document(doc_id: str, filename: str, blob_name: str, file_size: int) -> dict:
    doc = {
        "id": doc_id,
        "type": "document",
        "filename": filename,
        "blob_name": blob_name,
        "status": "processing",
        "file_size": int(file_size),
        "chunks_count": 0,
        "uploaded_at": now_iso(),
        "error": None,
        "chunks": [],
    }
    container = get_cosmos_container()
    container.create_item(body=doc)
    return doc


def get_document(doc_id: str) -> Optional[dict]:
    container = get_cosmos_container()
    try:
        return container.read_item(item=doc_id, partition_key=doc_id)
    except Exception:
        return None


def update_document(doc: dict) -> None:
    container = get_cosmos_container()
    # replace_item requires both item id and body.
    container.replace_item(item=doc["id"], body=doc)


def delete_document(doc_id: str) -> bool:
    container = get_cosmos_container()
    try:
        container.delete_item(item=doc_id, partition_key=doc_id)
        return True
    except Exception:
        return False


def list_documents(limit: int = 200) -> List[dict]:
    container = get_cosmos_container()
    # Cosmos SQL has no bare LIMIT — use OFFSET/LIMIT with a parameter.
    query = (
        "SELECT c.id, c.filename, c.status, c.file_size, c.chunks_count, "
        "c.uploaded_at, c.error FROM c WHERE c.type = 'document' "
        "ORDER BY c.uploaded_at DESC OFFSET 0 LIMIT @n"
    )
    items = container.query_items(
        query=query,
        parameters=[{"name": "@n", "value": int(limit)}],
        enable_cross_partition_query=True,
    )
    return list(items)


def iter_all_documents_with_chunks() -> Iterable[dict]:
    """Yield full documents including chunk embeddings for retrieval."""
    container = get_cosmos_container()
    query = (
        "SELECT * FROM c WHERE c.type = 'document' AND c.status = 'ready' "
        "OFFSET 0 LIMIT @n"
    )
    items = container.query_items(
        query=query,
        parameters=[{"name": "@n", "value": 1000}],
        enable_cross_partition_query=True,
    )
    for it in items:
        yield it
