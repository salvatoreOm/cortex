import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document
from app.repositories import document_repo
from app.schemas.document import DocumentRead
from app.services.ingestion_service import UnsupportedFileTypeError, ingest_upload

router = APIRouter(prefix="/documents", tags=["documents"])

# Real auth lands in Phase 4. Until then every upload belongs to this one
# seeded dev user (see alembic/versions/0002_*.py) so the user_id FK is satisfied.
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)) -> Document:
    try:
        return await ingest_upload(db, user_id=DEV_USER_ID, file=file)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[DocumentRead])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[Document]:
    return await document_repo.list_documents(db, user_id=DEV_USER_ID)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Document:
    document = await document_repo.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
