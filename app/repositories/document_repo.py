import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, SourceType


async def create_document(
    db: AsyncSession, *, user_id: uuid.UUID, title: str, source_type: SourceType
) -> Document:
    document = Document(user_id=user_id, title=title, source_type=source_type, status=DocumentStatus.pending)
    db.add(document)
    await db.flush()
    return document


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return await db.get(Document, document_id)


async def list_documents(db: AsyncSession, *, user_id: uuid.UUID) -> list[Document]:
    query = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())
