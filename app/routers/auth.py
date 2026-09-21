from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key, hash_api_key
from app.db.session import get_db
from app.repositories import user_repo
from app.schemas.user import SignupRequest, SignupResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> SignupResponse:
    """Create a user and hand back an API key. There's no login endpoint -
    this key IS the credential; keep it, it's shown here exactly once.
    """
    existing = await user_repo.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    api_key = generate_api_key()
    user = await user_repo.create_user(db, email=payload.email, api_key_hash=hash_api_key(api_key))
    await db.commit()
    await db.refresh(user)

    return SignupResponse(id=user.id, email=user.email, api_key=api_key, created_at=user.created_at)
