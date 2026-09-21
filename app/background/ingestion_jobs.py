import logging
import uuid

from app.db.session import async_session_factory
from app.repositories import document_repo
from app.services import ingestion_service

logger = logging.getLogger(__name__)


async def embed_document_chunks(document_id: uuid.UUID) -> None:
    """FastAPI BackgroundTasks entry point: embed one document's chunks.

    This runs after the upload response has already gone out, so the
    request's DB session is gone by then - open a fresh one here instead of
    trying to reuse it.
    """
    async with async_session_factory() as db:
        document = await document_repo.get_document(db, document_id)
        if document is None:
            logger.error("embed_document_chunks: document %s no longer exists", document_id)
            return
        await ingestion_service.embed_chunks(db, document)
