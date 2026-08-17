"""Pydantic models used by the API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    id: str
    filename: str
    status: str
    file_size: int = 0
    chunks_count: int = 0
    uploaded_at: Optional[str] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    id: str
    filename: str
    status: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: Optional[int] = None


class SourceChunk(BaseModel):
    document_id: str
    document_name: str
    page: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


class HealthResponse(BaseModel):
    status: str
