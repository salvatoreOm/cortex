import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repo


def generate_api_key() -> str:
    """A random, URL-safe API key handed to the client once, at signup."""
    return secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    """We only ever store this hash, never the raw key - same idea as password hashing."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_user(
    x_api_key: str | None = Header(
        default=None, alias="X-API-Key", description="API key returned by POST /auth/signup"
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    # x_api_key is Optional so a missing header is a 401 like a wrong one,
    # not FastAPI's default 422 "missing header" validation error.
    user = await user_repo.get_by_api_key_hash(db, hash_api_key(x_api_key)) if x_api_key else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return user
