from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401 - registers every table on Base.metadata before any query runs
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import engine
from app.routers import documents, health

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health.router)
app.include_router(documents.router)
