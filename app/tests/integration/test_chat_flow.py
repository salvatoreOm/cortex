import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import async_session_factory
from app.main import app

# These tests hit the real Postgres container and the real Azure AI Foundry
# endpoint configured in .env - they're integration tests, not unit tests.
# They cost a small amount of real API usage each run.


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _signup(client: AsyncClient) -> tuple[str, str]:
    email = f"pytest-{uuid.uuid4().hex[:12]}@example.com"
    resp = await client.post("/auth/signup", json={"email": email})
    assert resp.status_code == 201
    return resp.json()["api_key"], email


def _parse_sse(lines: list[str]) -> tuple[str, dict]:
    """Reassemble the streamed answer text and pull out the final `done`
    event's payload (SSE splits tokens mid-word, so we can't just substring-
    match the raw framed text).
    """
    full_text = ""
    done_payload: dict = {}
    current_event: str | None = None
    for line in lines:
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ")
        elif line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
            if current_event == "token":
                full_text += payload["delta"]
            elif current_event == "done":
                done_payload = payload
    return full_text, done_payload


async def _cleanup_user(email: str) -> None:
    # chunks/messages cascade off documents/chat_sessions, but documents and
    # chat_sessions themselves don't cascade off users, so delete those first.
    async with async_session_factory() as db:
        await db.execute(
            text("DELETE FROM chat_sessions WHERE user_id = (SELECT id FROM users WHERE email = :email)"),
            {"email": email},
        )
        await db.execute(
            text("DELETE FROM documents WHERE user_id = (SELECT id FROM users WHERE email = :email)"),
            {"email": email},
        )
        await db.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        await db.commit()


async def test_upload_then_chat_answers_grounded_in_document(client: AsyncClient):
    """Upload a document containing a fact the model can't already know, then
    ask a chat question about it, and check the streamed answer and its
    citation both point back to the real source.
    """
    api_key, email = await _signup(client)
    headers = {"X-API-Key": api_key}

    try:
        secret = "pineapple-lighthouse-42"
        content = (
            f"Cortex's test suite uses a secret code word: {secret}. "
            "This code word exists only to prove retrieval-augmented answers are grounded."
        ).encode()
        files = {"file": ("secret.txt", content, "text/plain")}
        resp = await client.post("/documents/upload", headers=headers, files=files)
        assert resp.status_code == 201
        document = resp.json()
        assert document["status"] == "processing"

        # By the time the upload call returns, the background embedding task
        # has already run (BackgroundTasks execute inside the same ASGI call
        # that httpx awaits) - but we still poll defensively.
        for _ in range(20):
            resp = await client.get(f"/documents/{document['id']}", headers=headers)
            if resp.json()["status"] in ("done", "failed"):
                break
        assert resp.json()["status"] == "done"

        resp = await client.post(
            "/chat/sessions", headers=headers, json={"title": "integration test"}
        )
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        events: list[str] = []
        async with client.stream(
            "POST",
            f"/chat/sessions/{session_id}/messages",
            headers=headers,
            json={"content": "What is the secret code word? Reply with just the code word."},
        ) as stream_resp:
            assert stream_resp.status_code == 200
            async for line in stream_resp.aiter_lines():
                events.append(line)
        full_text, done_payload = _parse_sse(events)

        assert secret in full_text
        assert done_payload["citations"][0]["document_title"] == "secret.txt"

        # The full conversation should also be readable back afterwards, with
        # the same citation resolved from source_chunk_ids.
        resp = await client.get(f"/chat/sessions/{session_id}/messages", headers=headers)
        assert resp.status_code == 200
        messages = resp.json()
        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert secret in messages[1]["content"]
        assert messages[1]["citations"][0]["document_title"] == "secret.txt"
    finally:
        await _cleanup_user(email)


async def test_chat_session_is_isolated_per_user(client: AsyncClient):
    api_key_a, email_a = await _signup(client)
    api_key_b, email_b = await _signup(client)

    try:
        resp = await client.post(
            "/chat/sessions", headers={"X-API-Key": api_key_a}, json={"title": "private"}
        )
        session_id = resp.json()["id"]

        resp = await client.get(
            f"/chat/sessions/{session_id}/messages", headers={"X-API-Key": api_key_b}
        )
        assert resp.status_code == 404
    finally:
        await _cleanup_user(email_a)
        await _cleanup_user(email_b)
