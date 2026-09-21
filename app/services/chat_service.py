import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.models.chunk import Chunk
from app.models.message import Message, MessageRole
from app.repositories import chat_repo, chunk_repo
from app.schemas.chat import Citation, MessageRead
from app.services import azure_llm_service, retrieval_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using only the "
    "context below, drawn from their own uploaded documents. If the context "
    "doesn't contain the answer, say you don't know - never make things up."
)
# Kept small on purpose: this is a learning project, not a production system,
# so a simple cutoff is enough context-window management for now.
MAX_HISTORY_MESSAGES = 10
TOP_K_CHUNKS = 5


def _build_messages(history: list[Message], chunks: list[Chunk], question: str) -> list[dict[str, str]]:
    if chunks:
        context = "\n\n".join(
            f'[{i + 1}] (from "{chunk.document.title}"): {chunk.content}'
            for i, chunk in enumerate(chunks)
        )
        system = f"{SYSTEM_PROMPT}\n\nContext:\n{context}"
    else:
        system = f"{SYSTEM_PROMPT}\n\n(No relevant context was found in the user's documents.)"

    messages = [{"role": "system", "content": system}]
    for message in history[-MAX_HISTORY_MESSAGES:]:
        messages.append({"role": message.role.value, "content": message.content})
    messages.append({"role": "user", "content": question})
    return messages


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def _chunk_to_citation(chunk: Chunk) -> dict:
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "document_title": chunk.document.title,
        "chunk_index": chunk.chunk_index,
    }


async def stream_reply(
    db: AsyncSession, *, session: ChatSession, question: str
) -> AsyncGenerator[bytes, None]:
    """Save the user's question, retrieve context, stream the assistant's reply
    over SSE, then persist the full assistant message with its citations.

    Runs inside the request (not a background task), so it's safe to keep
    using the request's own `db` session throughout.
    """
    history = await chat_repo.list_messages(db, session.id)
    await chat_repo.create_message(
        db, session_id=session.id, role=MessageRole.user, content=question
    )

    try:
        chunks = await retrieval_service.retrieve_relevant_chunks(
            db, user_id=session.user_id, query=question, top_k=TOP_K_CHUNKS
        )
    except Exception:
        logger.exception("Retrieval failed for session %s", session.id)
        chunks = []

    messages = _build_messages(history, chunks, question)

    full_text = ""
    try:
        async for delta in azure_llm_service.stream_chat_completion(messages):
            full_text += delta
            yield _sse("token", {"delta": delta})
    except Exception:
        logger.exception("Chat completion failed for session %s", session.id)
        yield _sse("error", {"detail": "The assistant failed to generate a reply."})
        await db.commit()
        return

    source_chunk_ids = [chunk.id for chunk in chunks] or None
    assistant_message = await chat_repo.create_message(
        db,
        session_id=session.id,
        role=MessageRole.assistant,
        content=full_text,
        source_chunk_ids=source_chunk_ids,
    )
    await db.commit()

    yield _sse(
        "done",
        {
            "message_id": str(assistant_message.id),
            "citations": [_chunk_to_citation(chunk) for chunk in chunks],
        },
    )


async def get_history(db: AsyncSession, session: ChatSession) -> list[MessageRead]:
    """Full conversation history with citations resolved from source_chunk_ids."""
    messages = await chat_repo.list_messages(db, session.id)

    all_chunk_ids: set[uuid.UUID] = set()
    for message in messages:
        if message.source_chunk_ids:
            all_chunk_ids.update(message.source_chunk_ids)

    chunks_by_id: dict[uuid.UUID, Chunk] = {}
    if all_chunk_ids:
        chunks = await chunk_repo.get_chunks_by_ids(db, list(all_chunk_ids))
        chunks_by_id = {chunk.id: chunk for chunk in chunks}

    result = []
    for message in messages:
        citations = [
            Citation(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                chunk_index=chunk.chunk_index,
            )
            for chunk_id in (message.source_chunk_ids or [])
            if (chunk := chunks_by_id.get(chunk_id)) is not None
        ]
        result.append(
            MessageRead(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                citations=citations,
            )
        )
    return result
