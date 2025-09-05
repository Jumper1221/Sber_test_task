from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.models import User
from app.schemas.auth import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def register_user(session: AsyncSession, data: UserCreate) -> dict:
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = pwd_context.hash(data.password)
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed_password,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    access_token = create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


async def authenticate_user(session: AsyncSession, data: UserCreate) -> dict:
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not pwd_context.verify(data.password, user.hashed_password):
        return None

    access_token = create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
