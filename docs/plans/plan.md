# Project Plan: Personal AI Knowledge Assistant (RAG System)

## 1. Project Overview

**What it is:** A personal, self-hosted RAG (Retrieval-Augmented Generation) system where users upload documents (PDFs, text, notes, links), and query their own knowledge base through a conversational interface. The system retrieves relevant context from stored documents and uses an LLM (via Azure AI Foundry) to generate grounded, cited answers.

**Why build it:** To gain hands-on, production-grade experience across backend engineering (FastAPI, async, layered architecture), data engineering (Postgres, pgvector, schema design), background job processing, and applied AI engineering (embeddings, chunking, RAG pipelines, streaming) — all in one cohesive system.

**Timeline:** 3–4 days for core build (Phases 0–4). Phase 5 is explicitly future scope.

**Frontend:** React/Next.js (vibe-coded, not covered in this plan — this plan is backend-focused).

---

## 2. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| API Framework | **FastAPI** (async) | Core backend |
| Language | **Python 3.11+** | |
| LLM + Embeddings | **Azure AI Foundry** | Chat completions + embedding model |
| Relational DB | **PostgreSQL** | Users, documents, sessions, messages |
| Vector Store | **pgvector** (Postgres extension) | Chunk embeddings, similarity search |
| ORM | **SQLAlchemy (async)** + `asyncpg` driver | Raw SQL only for vector similarity queries if needed |
| Migrations | **Alembic** | Schema versioning |
| Background Jobs | **FastAPI `BackgroundTasks`** (Phase 1–3) → **Celery/arq + Redis** (Phase 5 future scope) | Start simple, upgrade later |
| Containers | **Podman** (Postgres + Redis later) | Local dev environment |
| Validation | **Pydantic v2** | Request/response schemas |
| PDF/Text parsing | `pypdf` or `unstructured` | Document ingestion |
| Config management | `pydantic-settings` + `.env` | Environment variables |
| Testing | `pytest` + `pytest-asyncio` + `httpx` | Unit + integration tests |
| API Docs | FastAPI auto-generated (Swagger/OpenAPI) | Free with FastAPI |
| Logging | Python `logging` module (structured later) | Basic first, improve in Phase 5 |
| Streaming | Server-Sent Events (SSE) | For chat responses |

---

## 3. Architecture (Layered, FastAPI-idiomatic)

```
app/
├── main.py                 # FastAPI app entrypoint
├── core/
│   ├── config.py            # Settings (env vars, Azure keys, DB URL)
│   ├── logging.py           # Logging setup
│   └── security.py          # (Phase 4) auth utilities
├── db/
│   ├── session.py           # Async engine + session factory
│   └── base.py               # Base declarative model
├── models/                   # SQLAlchemy ORM models
│   ├── user.py
│   ├── document.py
│   ├── chunk.py
│   ├── chat_session.py
│   └── message.py
├── schemas/                   # Pydantic request/response models
│   ├── document.py
│   ├── chat.py
│   └── user.py
├── repositories/               # DB access layer (no business logic)
│   ├── document_repo.py
│   ├── chunk_repo.py
│   └── chat_repo.py
├── services/                    # Business logic / orchestration
│   ├── ingestion_service.py     # Chunking + embedding + storage orchestration
│   ├── retrieval_service.py     # Vector search + context assembly
│   ├── chat_service.py          # RAG pipeline: retrieve + prompt + LLM call
│   └── azure_llm_service.py     # Wrapper around Azure AI Foundry API calls
├── routers/                      # HTTP layer (handlers)
│   ├── documents.py
│   ├── chat.py
│   └── health.py
├── background/                    # Background job functions
│   └── ingestion_jobs.py
├── utils/
│   └── chunking.py                # Text chunking strategy
└── tests/
    ├── unit/
    └── integration/
alembic/
├── versions/
docker-compose.yml (or podman equivalent)
.env.example
requirements.txt / pyproject.toml
plan.md
README.md
```

**Layer responsibilities:**
- **Routers** — parse HTTP requests, call services, return responses. No business logic.
- **Services** — orchestration: chunking, calling Azure AI Foundry, coordinating retrieval + generation, triggering background jobs.
- **Repositories** — pure DB access (CRUD + vector search queries). No business logic.
- **Models** — SQLAlchemy table definitions.
- **Schemas** — Pydantic I/O contracts, decoupled from DB models.

---

## 4. Database Schema (Phase 1 target)

**users**
| column | type | notes |
|---|---|---|
| id | UUID (PK) | |
| email | string, unique | |
| created_at | timestamp | |

**documents**
| column | type | notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) | |
| title | string | |
| source_type | enum (pdf, text, link) | |
| status | enum (pending, processing, done, failed) | for background job tracking |
| created_at | timestamp | |

**chunks**
| column | type | notes |
|---|---|---|
| id | UUID (PK) | |
| document_id | UUID (FK → documents) | |
| content | text | raw chunk text |
| embedding | vector(N) | pgvector column, N = embedding model dimension |
| chunk_index | int | order within document |
| created_at | timestamp | |

**chat_sessions**
| column | type | notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) | |
| title | string | auto-generated or user-set |
| created_at | timestamp | |

**messages**
| column | type | notes |
|---|---|---|
| id | UUID (PK) | |
| session_id | UUID (FK → chat_sessions) | |
| role | enum (user, assistant) | |
| content | text | |
| source_chunk_ids | UUID[] (nullable) | for citation tracking |
| created_at | timestamp | |

**Indexes to add:** HNSW or IVFFlat index on `chunks.embedding`, FK indexes, `documents.status` index for job polling.

---

## 5. Phased Development Plan

### **Phase 0 — Environment & Project Setup** (Day 1, morning — ~2-3 hrs)
Goal: A running FastAPI app connected to a Postgres+pgvector container, with migrations working.

- [ ] Initialize git repo, `.gitignore`, `README.md`
- [ ] Set up Python virtual environment, `pyproject.toml`/`requirements.txt`
- [ ] Install: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `pgvector`, `pypdf`, `python-multipart`
- [ ] Set up Podman container for Postgres with `pgvector` extension enabled
- [ ] Write `docker-compose.yml`/Podman equivalent for local Postgres
- [ ] Create `core/config.py` with `.env` support (Azure endpoint, API key, DB URL)
- [ ] Set up async SQLAlchemy engine + session dependency (`db/session.py`)
- [ ] Initialize Alembic, configure for async engine
- [ ] Create a `/health` endpoint to confirm DB connectivity
- [ ] Verify: `uvicorn app.main:app --reload` runs, `/health` returns DB-connected status

**Deliverable:** Working skeleton app + DB connection confirmed.

---

### **Phase 1 — Core Data Layer & Document Ingestion (No AI yet)** (Day 1, afternoon–evening)
Goal: Upload a document, chunk it, and store chunks in Postgres (embeddings stubbed/skipped for now).

- [ ] Define SQLAlchemy models: `User`, `Document`, `Chunk`, `ChatSession`, `Message`
- [ ] Write Alembic migration, apply it, confirm tables + pgvector column created
- [ ] Define Pydantic schemas for `Document` create/read
- [ ] Build `repositories/document_repo.py`, `repositories/chunk_repo.py` (basic CRUD)
- [ ] Build `utils/chunking.py` — simple fixed-size chunking with overlap (e.g. 500 tokens, 50 overlap)
- [ ] Build `POST /documents/upload` endpoint (accepts PDF/text file)
- [ ] Build `services/ingestion_service.py`: extract text → chunk → save chunks (no embeddings yet, `status=pending`)
- [ ] Add `GET /documents/{id}` and `GET /documents` (list, with status)
- [ ] Write basic unit tests for chunking logic

**Deliverable:** Can upload a PDF, see it chunked and stored in Postgres, with status tracking.

---

### **Phase 2 — AI Integration: Embeddings + Vector Search** (Day 2, morning–afternoon)
Goal: Real embeddings via Azure AI Foundry, stored in pgvector, and working similarity search.

- [ ] Build `services/azure_llm_service.py` — wrapper for Azure AI Foundry:
  - `get_embedding(text: str) -> list[float]`
  - `get_chat_completion(messages: list) -> str` (used later in Phase 3)
- [ ] Update `ingestion_service.py`: after chunking, call `get_embedding()` per chunk, store vector in `chunks.embedding`
- [ ] Move embedding generation into a **background task** (`FastAPI BackgroundTasks`) so upload endpoint returns immediately; update `document.status` as it progresses (`pending` → `processing` → `done`/`failed`)
- [ ] Build `repositories/chunk_repo.py` vector search method (cosine similarity via pgvector, raw SQL or `pgvector.sqlalchemy` comparator)
- [ ] Build `services/retrieval_service.py`: given a query, embed it, retrieve top-k relevant chunks
- [ ] Build a test endpoint `POST /documents/search` to manually verify retrieval quality before wiring into chat
- [ ] Handle failure cases: embedding API timeout/error → mark document `failed`, log reason

**Deliverable:** Upload a document, background job embeds it, and you can retrieve relevant chunks for a test query.

---

### **Phase 3 — RAG Chat Pipeline** (Day 2 evening – Day 3)
Goal: Full conversational RAG — ask a question, get a grounded, cited answer, with multi-turn memory.

- [ ] Build `POST /chat/sessions` — create a new chat session
- [ ] Build `POST /chat/sessions/{id}/messages` — send a message:
  1. Save user message
  2. Retrieve relevant chunks (via `retrieval_service`)
  3. Assemble prompt (system prompt + retrieved context + chat history + user question)
  4. Call Azure AI Foundry chat completion
  5. Save assistant message (with `source_chunk_ids` for citations)
  6. Return response
- [ ] Implement **streaming** response via SSE (`StreamingResponse` in FastAPI) for a real chat feel
- [ ] Build `GET /chat/sessions/{id}/messages` — fetch conversation history
- [ ] Handle context window management: truncate/limit chat history + retrieved chunks sent to LLM
- [ ] Add citation formatting — return which document/chunk each answer drew from
- [ ] Write integration tests: upload → ask question → verify answer references correct source

**Deliverable:** End-to-end working RAG chat — this is your functional MVP.

---

### **Phase 4 — Hardening, Auth Basics, and Polish** (Day 3 evening – Day 4)
Goal: Make it robust enough to demo and safe enough to not embarrass yourself.

- [ ] Add basic auth (simple API key or JWT — doesn't need to be enterprise-grade)
- [ ] Scope all documents/chats to `user_id` properly (no cross-user data leaks)
- [ ] Add proper error handling + consistent error response schema across all endpoints
- [ ] Add request validation edge cases (empty file, unsupported file type, oversized upload)
- [ ] Add logging at key points (ingestion start/end, retrieval, LLM calls, errors)
- [ ] Add `DELETE /documents/{id}` (cascade delete chunks)
- [ ] Write a proper `README.md`: setup instructions, architecture diagram, how to run locally with Podman
- [ ] Manual end-to-end test pass: upload 2-3 varied documents, run 5-10 real questions, check answer quality and citations
- [ ] Clean up: remove dead code, consistent naming, docstrings on services

**Deliverable:** A demo-ready, reasonably robust backend you'd be comfortable showing in an interview or portfolio.

---

## 6. Suggested Day-by-Day Breakdown (3–4 Days)

| Day | Focus |
|---|---|
| **Day 1** | Phase 0 (setup) + Phase 1 (ingestion, no AI) |
| **Day 2** | Phase 2 (embeddings + vector search) + start Phase 3 (chat pipeline) |
| **Day 3** | Finish Phase 3 (streaming, citations, multi-turn) + start Phase 4 |
| **Day 4 (buffer)** | Finish Phase 4 (auth, polish, testing, README) + connect frontend if time allows |

---

## 7. Working with Claude Code — Suggested Workflow

- Work **phase by phase**, not file by file — ask Claude Code to implement one full phase at a time, then test before moving on.
- After each phase, **run the app and manually verify** the deliverable before proceeding (don't stack unverified phases).
- Keep this `plan.md` in your repo root — reference it explicitly in prompts (e.g., "Implement Phase 1 from plan.md") so Claude Code has consistent context.
- Commit after each completed phase (`git commit -m "Phase 1: document ingestion complete"`) — gives you rollback points and a clean history.
- When something breaks, paste the actual error/traceback rather than describing it — faster and more accurate fixes.

---

## 8. Future Scope (Phase 5+) — Explicitly Deferred

These are **intentionally excluded** from the initial 3–4 day build. Once Phases 0–4 are solid, this is the natural next-level roadmap:

### 5.1 Performance & Scalability
- Replace `FastAPI BackgroundTasks` with a **real task queue** (Celery or `arq`) + **Redis** as broker — enables retries, concurrency control, job monitoring
- Add **caching**:
  - Inline: in-memory caching (e.g., `functools.lru_cache`) for repeated embedding calls on identical text
  - Non-inline: **Redis-based semantic cache** — cache LLM responses for semantically similar queries (huge cost/latency win)
- **Load balancing** across multiple Azure AI Foundry deployments/regions for higher throughput and failover
- Connection pooling tuning for Postgres under load
- Rate limiting (per-user, per-endpoint) via middleware or `slowapi`

### 5.2 Advanced RAG Techniques
- **Reranking** retrieved chunks (cross-encoder or LLM-based reranker) before sending to the LLM
- **Semantic/recursive chunking** instead of fixed-size chunking
- **Hybrid search** — combine vector similarity with keyword (BM25/full-text) search in Postgres
- **Query rewriting/expansion** for better retrieval on vague questions

### 5.3 Agentic Capabilities
- Introduce **LangGraph** or a custom agent loop for multi-step reasoning: "decide whether to retrieve, summarize, or answer directly"
- Tool-use: let the assistant take actions (e.g., "create a study guide file," "schedule a reminder") beyond just answering
- Multi-document synthesis agents (compare/contrast across sources autonomously)

### 5.4 Observability & Reliability
- Structured logging (JSON logs) + correlation IDs across requests
- Metrics/tracing (Prometheus + Grafana, or OpenTelemetry)
- Cost tracking dashboard for Azure AI Foundry token usage
- Proper retry/backoff strategies for external API failures

### 5.5 Product Enhancements
- Multi-modal ingestion (images, audio transcripts)
- Shareable/public chat sessions
- Document versioning (re-ingest updated docs without duplicating)
- Fine-grained citation UI (highlight exact source passage, not just document)

### 5.6 Infrastructure Maturity
- CI/CD pipeline (GitHub Actions: lint, test, build on push)
- Containerize the full app (not just DB) for consistent deployment
- Move from Podman local dev to a proper deployment target (Azure Container Apps, Fly.io, etc.)
- Secrets management (Azure Key Vault instead of `.env`)

---

## 9. Success Criteria for the Core Build (Phases 0–4)

By the end of Day 3–4, you should be able to:
1. Upload a PDF and watch it move through `pending → processing → done` status
2. Ask a natural language question and get an answer grounded in your uploaded documents
3. See which document/chunk the answer was sourced from
4. Continue a multi-turn conversation with context retained
5. Explain, in an interview setting, every architectural decision you made and why

If you can do all five, the core project is a success — everything else is Phase 5 polish.
