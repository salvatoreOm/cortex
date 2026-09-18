# Setup Guide

## 1. Turn on container
- Start only `lms-postgres` in Podman.
- Leave azurite, rabbitmq, redis OFF (not needed yet).

## 2. Enable pgvector in Postgres
- Image used: `pgvector/pgvector:pg16` (pgvector pre-installed).
- Data saved in volume: `cortex_pg_data` (survives container restart/kill).
- Connect to `lms-postgres`.
- Run: `CREATE EXTENSION IF NOT EXISTS vector;`

## 3. Project folder setup
- Create project folder (e.g. `app/`).
- Init git: `git init`
- Add `.gitignore` (python, .env, venv)

## 4. Python environment
- Use Python **3.11+** (we use 3.11 for now).
- `python3.11 -m venv venv`
- `source venv/bin/activate`
- Check: `python --version` → should show 3.11.x
- Create `requirements.txt` with:
  - fastapi
  - uvicorn
  - sqlalchemy[asyncio]
  - asyncpg
  - alembic
  - pydantic-settings
  - pgvector
  - pypdf
  - python-multipart
- `pip install -r requirements.txt`

## 5. Get API keys
- Go to Azure AI Foundry portal.
- Create/open a project.
- Deploy a chat model + an embedding model.
- Copy: endpoint URL, API key, deployment names.

## 6. .env file
Create `.env` with:
```
DATABASE_URL=postgresql+asyncpg://salvatoreom:omparihar%40123@localhost:5432/cortex_db
AZURE_AI_ENDPOINT=your-endpoint
AZURE_AI_KEY=your-key
AZURE_CHAT_DEPLOYMENT=your-chat-model-name
AZURE_EMBEDDING_DEPLOYMENT=your-embedding-model-name
```
Also make `.env.example` (same, no real values).

## 7. Verify
- Postgres container running.
- `vector` extension enabled.
- Python packages installed.
- `.env` filled with real keys.

You are ready to start Phase 0 coding.
