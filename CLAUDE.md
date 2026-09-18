# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

No application code exists yet — this repo currently holds only the plan and local dev infrastructure. The backend (FastAPI app under `app/`) has not been scaffolded. When implementing, follow `docs/plans/plan.md` phase by phase (see below); don't jump ahead to later phases before earlier ones are verified working.

## What this project is

A self-hosted RAG (Retrieval-Augmented Generation) system: users upload documents, the app chunks + embeds them, and answers questions grounded in that content via Azure AI Foundry (chat + embeddings). Full spec, tech stack, DB schema, and phased build plan: `docs/plans/plan.md`.

Tech stack (once built): FastAPI (async) + Python 3.11+, PostgreSQL with `pgvector`, SQLAlchemy (async) + `asyncpg`, Alembic migrations, Pydantic v2, SSE for chat streaming.

## Repo layout

```
docs/
├── plans/    — plan.md (full project spec, phases, DB schema, success criteria)
├── learning/ — reference explainers (Podman, DB connection strings, etc.)
└── setup.md  — step-by-step environment setup checklist
docker-compose.yml — local Postgres+pgvector container
```

When adding new docs, keep this convention: planning docs → `docs/plans/`, conceptual/reference explainers → `docs/learning/`, everything else project-specific → `docs/`.

## Local infrastructure (Podman)

Postgres runs in a container (`cortex-postgres`), not natively on the host — a native Homebrew Postgres was deliberately removed to avoid port 5432 conflicts. Don't install Postgres via brew/pip locally; always use the container.

```bash
podman-compose up -d      # start Postgres (pgvector/pgvector:pg16 image)
podman-compose down       # stop (data persists in the cortex_pg_data volume)
podman-compose logs -f postgres
```

If `podman-compose` isn't installed, the equivalent raw command is in `docs/personal_notes.md`.

Current container credentials (local dev only): user `salvatoreom`, db `cortex_db`, port `5432`. The password contains `@` — it must be URL-encoded as `%40` in any `DATABASE_URL` connection string (e.g. `postgresql+asyncpg://salvatoreom:omparihar%40123@localhost:5432/cortex_db`). Exact current values: `docs/personal_notes.md`.

pgvector extension must be enabled per-database: `CREATE EXTENSION IF NOT EXISTS vector;`

## Architecture (per plan.md, to be implemented)

Layered FastAPI structure — routers call services, services call repositories, repositories touch the DB. No business logic in routers or repositories.

- `routers/` — HTTP layer only: parse request, call a service, return response.
- `services/` — orchestration: chunking, Azure AI Foundry calls, RAG pipeline (retrieve → prompt → generate), background job coordination.
- `repositories/` — pure DB access (CRUD + pgvector similarity search). No business logic.
- `models/` — SQLAlchemy ORM tables.
- `schemas/` — Pydantic I/O contracts, decoupled from ORM models.

Core entities: `users`, `documents`, `chunks` (has the `vector` embedding column + pgvector index), `chat_sessions`, `messages` (stores `source_chunk_ids` for citations). Full schema in `docs/plans/plan.md` section 4.

Background work (document ingestion → chunk → embed) starts on FastAPI `BackgroundTasks` in early phases; a real queue (Celery/arq + Redis) is explicitly deferred to Phase 5 — don't introduce it early.

Build order follows `docs/plans/plan.md` section 5: Phase 0 (skeleton + DB connection) → Phase 1 (ingestion, no AI) → Phase 2 (embeddings + vector search) → Phase 3 (RAG chat + streaming) → Phase 4 (auth, hardening, polish). Phase 5+ (real task queue, caching, reranking, hybrid search, agentic features, observability) is explicitly out of scope until Phases 0–4 are solid.
