import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus, SourceType


class DocumentRead(BaseModel):
    """What we return to the client after upload, and for GET /documents(/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source_type: SourceType
    status: DocumentStatus
    created_at: datetime


class ChunkSearchRequest(BaseModel):
    """Body for POST /documents/search - a manual way to check retrieval quality."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkSearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    chunk_index: int
    content: str
