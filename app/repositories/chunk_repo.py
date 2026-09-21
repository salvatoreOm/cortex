import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import Chunk
from app.models.document import Document


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


async def search_similar_chunks(
    db: AsyncSession, *, user_id: uuid.UUID, query_embedding: list[float], top_k: int = 5
) -> list[Chunk]:
    """Find the top_k chunks (scoped to this user's documents) closest to
    query_embedding, using pgvector cosine distance - smaller is more similar.
    """
    query = (
        select(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .options(selectinload(Chunk.document))
        .where(Document.user_id == user_id, Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
