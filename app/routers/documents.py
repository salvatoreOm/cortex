import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.background.ingestion_jobs import embed_document_chunks
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.repositories import document_repo
from app.schemas.document import ChunkSearchRequest, ChunkSearchResult, DocumentRead
from app.services import retrieval_service
from app.services.ingestion_service import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    ingest_upload,
)

router = APIRouter(prefix="/documents", tags=["documents"])


async def _get_owned_document(db: AsyncSession, document_id: uuid.UUID, user: User) -> Document:
    document = await document_repo.get_document(db, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    try:
        document = await ingest_upload(db, user_id=current_user.id, file=file)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EmptyFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    if document.status == DocumentStatus.processing:
        # Chunks are saved; embedding them calls Azure, so it happens after
        # this response is already on its way back to the client.
        background_tasks.add_task(embed_document_chunks, document.id)

    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Document]:
    return await document_repo.list_documents(db, user_id=current_user.id)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    return await _get_owned_document(db, document_id, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    document = await _get_owned_document(db, document_id, current_user)
    await document_repo.delete_document(db, document)
    await db.commit()


@router.post("/search", response_model=list[ChunkSearchResult])
async def search_documents(
    payload: ChunkSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChunkSearchResult]:
    """Manual endpoint for sanity-checking retrieval quality outside of a chat session."""
    chunks = await retrieval_service.retrieve_relevant_chunks(
        db, user_id=current_user.id, query=payload.query, top_k=payload.top_k
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
