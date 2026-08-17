"""Semantic retrieval: embed query, cosine-rank stored chunks, return top N."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from . import config, repository
from .openai_service import embed_query


@dataclass
class Retrieved:
    document_id: str
    document_name: str
    page: int
    text: str
    score: float


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def retrieve(question: str, top_k: int | None = None) -> List[Retrieved]:
    k = top_k or config.TOP_K
    q_vec = np.asarray(embed_query(question), dtype=np.float32)

    scored: List[Retrieved] = []
    for doc in repository.iter_all_documents_with_chunks():
        doc_id = doc["id"]
        name = doc.get("filename", "")
        for ch in doc.get("chunks", []):
            emb = ch.get("embedding")
            if not emb:
                continue
            score = _cosine(q_vec, np.asarray(emb, dtype=np.float32))
            scored.append(
                Retrieved(
                    document_id=doc_id,
                    document_name=name,
                    page=int(ch.get("page", 0)),
                    text=ch.get("text", ""),
                    score=score,
                )
            )
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:k]
