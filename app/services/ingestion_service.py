import logging
import uuid
from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, SourceType
from app.repositories import chunk_repo, document_repo
from app.utils.chunking import chunk_text

logger = logging.getLogger(__name__)

# Phase 1 only understands these two; "link" ingestion is future scope.
CONTENT_TYPE_TO_SOURCE_TYPE = {
    "application/pdf": SourceType.pdf,
    "text/plain": SourceType.text,
}


class UnsupportedFileTypeError(Exception):
    """Raised when the uploaded file's content type isn't one we can ingest."""


def _extract_text(raw: bytes, source_type: SourceType) -> str:
    if source_type == SourceType.pdf:
        reader = PdfReader(BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8")


async def ingest_upload(db: AsyncSession, *, user_id: uuid.UUID, file: UploadFile) -> Document:
    """Save the upload as a Document, then extract -> chunk -> store chunks.

    No embeddings yet (that's Phase 2) - this just proves the ingestion
    pipeline and status tracking work end to end.
    """
    source_type = CONTENT_TYPE_TO_SOURCE_TYPE.get(file.content_type or "")
    if source_type is None:
        raise UnsupportedFileTypeError(f"Unsupported content type: {file.content_type}")

    document = await document_repo.create_document(
        db, user_id=user_id, title=file.filename or "untitled", source_type=source_type
    )

    try:
        document.status = DocumentStatus.processing
        await db.flush()

        raw = await file.read()
        text = _extract_text(raw, source_type)
        pieces = chunk_text(text)

        if pieces:
            await chunk_repo.create_chunks(db, document_id=document.id, texts=pieces)
            document.status = DocumentStatus.done
        else:
            # No extractable text (e.g. a scanned/empty PDF) - not a bug, just nothing to store.
            document.status = DocumentStatus.failed
    except Exception:
        logger.exception("Ingestion failed for document %s", document.id)
        document.status = DocumentStatus.failed

    await db.commit()
    await db.refresh(document)
    return document
