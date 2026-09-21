import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk


async def create_chunks(db: AsyncSession, *, document_id: uuid.UUID, texts: list[str]) -> list[Chunk]:
    chunks = [
        Chunk(document_id=document_id, content=text, chunk_index=index)
        for index, text in enumerate(texts)
    ]
    db.add_all(chunks)
    await db.flush()
    return chunks


async def list_chunks_for_document(db: AsyncSession, document_id: uuid.UUID) -> list[Chunk]:
    query = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
