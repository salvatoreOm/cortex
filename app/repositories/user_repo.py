from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_user(db: AsyncSession, *, email: str, api_key_hash: str) -> User:
    user = User(email=email, api_key_hash=api_key_hash)
    db.add(user)
    await db.flush()
    return user


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_by_api_key_hash(db: AsyncSession, api_key_hash: str) -> User | None:
    query = select(User).where(User.api_key_hash == api_key_hash)
    result = await db.execute(query)
    return result.scalar_one_or_none()
