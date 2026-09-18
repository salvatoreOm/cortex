# Learning: Database Connection String

## Example
```
postgresql+asyncpg://cortex_user:devpassword@localhost:5432/cortex_db
```
Tells your Python app how to find and log into the database. Same idea as a website URL, just for a DB.

## Breakdown

| Piece | Meaning |
|---|---|
| `postgresql` | Database type — "talking to Postgres" |
| `+asyncpg` | Driver — Python library used to talk to Postgres. Async, needed for FastAPI async endpoints |
| `cortex_user` | Username to log in as |
| `devpassword` | Password for that user |
| `localhost` | Host — where Postgres runs (container port mapped to your machine) |
| `5432` | Port — Postgres default port |
| `cortex_db` | Which database on the server to connect to |

General pattern: `dialect+driver://user:password@host:port/database_name`

## Why `+asyncpg` matters
SQLAlchemy supports many drivers per database. If you used `psycopg2` (sync driver) by mistake, your async FastAPI code would block on every DB call — killing the point of using async. Driver choice is a real performance decision, not just syntax.
