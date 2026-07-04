from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["app_store", "play_store", "reddit"]


class QueryFilters(BaseModel):
    sources: list[SourceType] | None = None
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    date_from: str | None = None
    date_to: str | None = None
    segments: list[str] | None = None
    app_name: str | None = None


class QueryOptions(BaseModel):
    top_k: int = Field(default=8, ge=1, le=30)
    stream: bool = False


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    filters: QueryFilters | None = None
    options: QueryOptions | None = None


class Citation(BaseModel):
    id: str
    excerpt: str
    source: SourceType
    rating: int | None = None
    url: str | None = None
    created_at: str | None = None
    relevance_score: float


class QueryMetadata(BaseModel):
    retrieved_count: int
    sources_used: list[SourceType]
    model: str
    latency_ms: int
    openai_available: bool = True


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: QueryMetadata


class IngestTriggerRequest(BaseModel):
    count: int | None = Field(default=None, ge=1, le=1000)
    use_sample: bool = False
    sources: list[SourceType] | None = None


class IngestStatusResponse(BaseModel):
    status: str
    total_documents: int
    sources: dict[str, int]
    last_ingestion_at: datetime | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    chroma: str
    openai_configured: bool
    document_count: int
