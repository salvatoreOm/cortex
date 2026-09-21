import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.background.ingestion_jobs import embed_document_chunks
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.repositories import document_repo
from app.schemas.document import ChunkSearchRequest, ChunkSearchResult, DocumentRead
from app.services import retrieval_service
from app.services.ingestion_service import UnsupportedFileTypeError, ingest_upload

router = APIRouter(prefix="/documents", tags=["documents"])

# Real auth lands in Phase 4. Until then every upload belongs to this one
# seeded dev user (see alembic/versions/0002_*.py) so the user_id FK is satisfied.
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> Document:
    try:
        document = await ingest_upload(db, user_id=DEV_USER_ID, file=file)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if document.status == DocumentStatus.processing:
        # Chunks are saved; embedding them calls Azure, so it happens after
        # this response is already on its way back to the client.
        background_tasks.add_task(embed_document_chunks, document.id)

    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[Document]:
    return await document_repo.list_documents(db, user_id=DEV_USER_ID)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Document:
    document = await document_repo.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/search", response_model=list[ChunkSearchResult])
async def search_documents(
    payload: ChunkSearchRequest, db: AsyncSession = Depends(get_db)
) -> list[ChunkSearchResult]:
    """Manual endpoint to sanity-check retrieval quality before Phase 3 wires this into chat."""
    chunks = await retrieval_service.retrieve_relevant_chunks(
        db, user_id=DEV_USER_ID, query=payload.query, top_k=payload.top_k
    )
    return [
        ChunkSearchResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
        )
        for chunk in chunks
    ]
