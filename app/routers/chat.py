import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.user import User
from app.repositories import chat_repo
from app.schemas.chat import ChatSessionCreate, ChatSessionRead, MessageCreate, MessageRead
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_owned_session(db: AsyncSession, session_id: uuid.UUID, user: User) -> ChatSession:
    session = await chat_repo.get_session(db, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return session


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    session = await chat_repo.create_session(db, user_id=current_user.id, title=payload.title)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ChatSession]:
    return await chat_repo.list_sessions(db, user_id=current_user.id)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    session = await _get_owned_session(db, session_id, current_user)
    return StreamingResponse(
        chat_service.stream_reply(db, session=session, question=payload.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def get_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    session = await _get_owned_session(db, session_id, current_user)
    return await chat_service.get_history(db, session)
