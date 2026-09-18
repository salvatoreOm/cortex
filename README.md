# cortex

Self-hosted RAG system: upload documents, then ask questions grounded in them.
FastAPI (async) + Postgres/pgvector + Azure AI Foundry.

## Local setup

```bash
cp .env.example .env              # fill in DATABASE_URL and Azure values
podman-compose up -d              # Postgres + pgvector on :5432
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head              # apply migrations (enables pgvector)
uvicorn app.main:app --reload
```

- Health check: `GET http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- If the DB password contains special characters, URL-encode them in
  `DATABASE_URL` (e.g. `@` → `%40`).
