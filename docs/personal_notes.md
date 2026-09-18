# Personal Notes

## Postgres + pgvector setup (what I did)

1. Pulled image: `podman pull pgvector/pgvector:pg16` — Postgres with pgvector pre-installed.
2. Created volume: `podman volume create cortex_pg_data` — keeps data safe on container kill/upgrade.
3. Ran the container:

   ```bash
   podman run -d \
     --name cortex-postgres \
     -e POSTGRES_USER=salvatoreom \
     -e POSTGRES_PASSWORD='omparihar@123' \
     -e POSTGRES_DB=cortex_db \
     -p 5432:5432 \
     -v cortex_pg_data:/var/lib/postgresql/data \
     pgvector/pgvector:pg16
   ```

4. Verified: `podman ps`
5. Enabled extension:

   ```bash
   podman exec -it cortex-postgres psql -U salvatoreom -d cortex_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

6. `.env` connection string (password has `@`, must be URL-encoded as `%40`):

   ```env
   DATABASE_URL=postgresql+asyncpg://salvatoreom:omparihar%40123@localhost:5432/cortex_db
   ```

## Trade-off note

Without a named volume, killing the container wipes your DB.
This is non-negotiable even in local dev — you don't want to re-upload test documents every time you restart.

## See also

- Connection string breakdown → `docs/learning/database.md`
- YAML / docker-compose explainer → `docs/learning/podman.md`
- Compose file itself → `docker-compose.yml` (project root)
