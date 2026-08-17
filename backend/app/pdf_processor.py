"""PDF processing: extract pages, chunk with overlap."""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List

from pypdf import PdfReader

from . import config


@dataclass
class Chunk:
    text: str
    page: int
    index: int


def _split_with_overlap(text: str, size: int, overlap: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    out: List[str] = []
    for start in range(0, len(text), step):
        piece = text[start : start + size].strip()
        if piece:
            out.append(piece)
        if start + size >= len(text):
            break
    return out


def extract_and_chunk(pdf_bytes: bytes) -> List[Chunk]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    chunks: List[Chunk] = []
    idx = 0
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        for piece in _split_with_overlap(
            page_text, config.CHUNK_SIZE_CHARS, config.CHUNK_OVERLAP_CHARS
        ):
            chunks.append(Chunk(text=piece, page=page_no, index=idx))
            idx += 1
    return chunks
