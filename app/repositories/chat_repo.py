import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.models.message import Message, MessageRole


async def create_session(db: AsyncSession, *, user_id: uuid.UUID, title: str | None) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> ChatSession | None:
    return await db.get(ChatSession, session_id)


async def list_sessions(db: AsyncSession, *, user_id: uuid.UUID) -> list[ChatSession]:
    query = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_message(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    role: MessageRole,
    content: str,
    source_chunk_ids: list[uuid.UUID] | None = None,
) -> Message:
    message = Message(session_id=session_id, role=role, content=content, source_chunk_ids=source_chunk_ids)
    db.add(message)
    await db.flush()
    return message


async def list_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    query = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
