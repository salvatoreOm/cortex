# cortex

Self-hosted RAG (Retrieval-Augmented Generation) system: upload documents,
then ask questions and get answers grounded in them, with citations.
FastAPI (async) + Postgres/pgvector + Azure AI Foundry.

## Local setup

```bash
cp .env.example .env              # fill in DATABASE_URL and Azure values
podman-compose up -d              # Postgres + pgvector on :5432
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head              # apply migrations (creates tables, enables pgvector)
uvicorn app.main:app --reload
```

- API docs (Swagger UI): `http://localhost:8000/docs`
- Health check: `GET http://localhost:8000/health`
- If the DB password contains special characters, URL-encode them in
  `DATABASE_URL` (e.g. `@` → `%40`).

## Architecture

```
Router (HTTP only) -> Service (orchestration) -> Repository (DB access) -> Postgres/pgvector
                                |
                                v
                       Azure AI Foundry (embeddings + chat)
```

- `routers/` - parse the HTTP request, call a service, return a response. No business logic.
- `services/` - chunking, calling Azure, the RAG pipeline (retrieve -> prompt -> generate).
- `repositories/` - plain DB reads/writes (CRUD + pgvector similarity search). No business logic.
- `models/` - SQLAlchemy tables. `schemas/` - Pydantic request/response shapes.
- `background/` - work that runs after an HTTP response has already been sent
  (right now: embedding a document's chunks, via FastAPI's `BackgroundTasks`).

## Using the API

Auth is a simple API key (see Phase 4 in `docs/plans/plan.md` for why - this
is a personal project, not a multi-tenant SaaS, so this is deliberately
lighter than a full login system). There's no login endpoint: the key from
signup **is** the credential, and it's shown exactly once.

```bash
# 1. Create a user, get an API key back (save it - it's shown once)
curl -X POST localhost:8000/auth/signup -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
# -> {"id": "...", "email": "...", "api_key": "..."}

KEY="paste-the-api_key-here"

# 2. Upload a document (PDF or plain text). It's chunked immediately;
#    embedding happens in the background, so status starts as "processing".
curl -X POST localhost:8000/documents/upload -H "X-API-Key: $KEY" \
  -F "file=@notes.txt;type=text/plain"

# 3. Check on it (status moves pending -> processing -> done/failed)
curl localhost:8000/documents/{id} -H "X-API-Key: $KEY"

# 4. Start a chat session
curl -X POST localhost:8000/chat/sessions -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"title": "my chat"}'
# -> {"id": "<session_id>", ...}

# 5. Ask a question - the reply streams back as Server-Sent Events
curl -N -X POST localhost:8000/chat/sessions/{session_id}/messages \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"content": "What does my document say about X?"}'

# 6. Read back the full conversation, with citations resolved
curl localhost:8000/chat/sessions/{session_id}/messages -H "X-API-Key: $KEY"
```

Every document and chat session is scoped to the API key that created it -
one user can never see, edit, or delete another user's data.

## Running tests

```bash
pytest
```

`app/tests/unit/` is pure logic, no external services. `app/tests/integration/`
signs up real test users and hits the real Postgres container **and** the
real Azure AI Foundry endpoint in `.env` - each run costs a small amount of
real API usage, and needs `podman-compose up -d` running first.

## Project status

Phases 0-4 from `docs/plans/plan.md` (learning docs, not shipped - see
`.gitignore`) are complete: ingestion, embeddings + vector search, streaming
RAG chat with citations, and basic auth/hardening. Phase 5+ (a real task
queue, caching, reranking, hybrid search, observability, etc.) is explicit
future scope and intentionally not built.
