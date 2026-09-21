import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.repositories import chunk_repo
from app.services.azure_llm_service import get_embedding


async def retrieve_relevant_chunks(
    db: AsyncSession, *, user_id: uuid.UUID, query: str, top_k: int = 5
) -> list[Chunk]:
    """Embed the query and return the top_k most similar chunks for this user."""
    query_embedding = await get_embedding(query)
    return await chunk_repo.search_similar_chunks(
        db, user_id=user_id, query_embedding=query_embedding, top_k=top_k
    )
