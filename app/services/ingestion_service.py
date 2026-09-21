import logging
import uuid
from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, SourceType
from app.repositories import chunk_repo, document_repo
from app.services.azure_llm_service import get_embedding
from app.utils.chunking import chunk_text

logger = logging.getLogger(__name__)

# Phase 1 only understands these two; "link" ingestion is future scope.
CONTENT_TYPE_TO_SOURCE_TYPE = {
    "application/pdf": SourceType.pdf,
    "text/plain": SourceType.text,
}

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB - plenty for a personal document store


class UnsupportedFileTypeError(Exception):
    """Raised when the uploaded file's content type isn't one we can ingest."""


class EmptyFileError(Exception):
    """Raised when the uploaded file has no bytes at all."""


class FileTooLargeError(Exception):
    """Raised when the uploaded file exceeds MAX_UPLOAD_BYTES."""


def _extract_text(raw: bytes, source_type: SourceType) -> str:
    if source_type == SourceType.pdf:
        reader = PdfReader(BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8")


async def ingest_upload(db: AsyncSession, *, user_id: uuid.UUID, file: UploadFile) -> Document:
    """Save the upload as a Document, then extract -> chunk -> store chunks.

    This part is fast (no network calls), so it stays synchronous - the
    caller responds to the client right after this returns. On success the
    document is left in `processing`, meaning "chunked, embeddings pending";
    the router hands it off to a background job (embed_chunks below) that
    fills in embeddings and moves it to `done`.
    """
    source_type = CONTENT_TYPE_TO_SOURCE_TYPE.get(file.content_type or "")
    if source_type is None:
        raise UnsupportedFileTypeError(f"Unsupported content type: {file.content_type}")

    raw = await file.read()
    if not raw:
        raise EmptyFileError("Uploaded file is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")

    logger.info("Ingestion started: %s (%s, %d bytes)", file.filename, source_type.value, len(raw))

    document = await document_repo.create_document(
        db, user_id=user_id, title=file.filename or "untitled", source_type=source_type
    )

    try:
        document.status = DocumentStatus.processing
        await db.flush()

        text = _extract_text(raw, source_type)
        pieces = chunk_text(text)

        if pieces:
            await chunk_repo.create_chunks(db, document_id=document.id, texts=pieces)
        else:
            # No extractable text (e.g. a scanned/empty PDF) - not a bug, just nothing to store.
            document.status = DocumentStatus.failed
    except Exception:
        logger.exception("Ingestion failed for document %s", document.id)
        document.status = DocumentStatus.failed

    await db.commit()
    await db.refresh(document)
    logger.info("Ingestion finished: document %s status=%s", document.id, document.status.value)
    return document


async def embed_chunks(db: AsyncSession, document: Document) -> None:
    """Embed every chunk of `document` (network calls to Azure) and flip its status.

    Called from the background job in app/background/ingestion_jobs.py, on a
    DB session of its own - never reuse the request's session here, since
    that one is already closed by the time a background task runs.
    """
    chunks = await chunk_repo.list_chunks_for_document(db, document.id)
    logger.info("Embedding started: document %s, %d chunks", document.id, len(chunks))
    try:
        for chunk in chunks:
            chunk.embedding = await get_embedding(chunk.content)
        document.status = DocumentStatus.done
    except Exception:
        logger.exception("Embedding failed for document %s", document.id)
        document.status = DocumentStatus.failed

    await db.commit()
    logger.info("Embedding finished: document %s status=%s", document.id, document.status.value)
