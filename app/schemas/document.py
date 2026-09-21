import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus, SourceType


class DocumentRead(BaseModel):
    """What we return to the client after upload, and for GET /documents(/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source_type: SourceType
    status: DocumentStatus
    created_at: datetime
