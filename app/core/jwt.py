import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import User
from app.models.token import RefreshToken
from app.schemas.auth import TokensPair


def get_token_hash(token: str) -> str:
    """Generate a hash for the given token."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a new access token."""

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    jwt_id = secrets.token_urlsafe(16)  # Unique identifier for the JWT

    to_encode = {"sub": str(user_id), "exp": expire, "jti": jwt_id}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from None

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None


async def create_refresh_token(db: AsyncSession, user_id: uuid.UUID):
    """Create a new refresh token."""
    token = secrets.token_urlsafe(64)
    token_hash = get_token_hash(token)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    #  т.е. мы подготавливаем данные к записи в бд, но не КОММИТИМ их
    new_refresh_token = RefreshToken(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at
    )
    db.add(new_refresh_token)
    await db.flush()

    # возвращаем нехэшированный токен для передачи пользователю
    return token


async def delete_refresh_token(db: AsyncSession, token: RefreshToken):
    """Delete a refresh token from the database."""
    await db.delete(token)


async def delete_expired_refresh_tokens_for_user(db: AsyncSession, user_id: uuid.UUID):
    """Remove expired refresh tokens from the database for a specific user."""
    query = delete(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.expires_at < datetime.now(timezone.utc),
    )
    await db.execute(query)


async def get_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    """Get a refresh token from the database."""
    token_hash = get_token_hash(token)
    query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_token_pair(db: AsyncSession, user_id: uuid.UUID) -> TokensPair:
    """Create a new access and refresh token pair."""
    try:
        access_token = create_access_token(user_id)
        refresh_token = await create_refresh_token(db, user_id)
        await db.commit()  # Commit the new refresh token to the database

        return TokensPair(access_token=access_token, refresh_token=refresh_token)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create token pair. Details: {e}",
        ) from e


async def update_tokens_pair(db: AsyncSession, incoming_token: str):
    """Update the access and refresh token pair."""

    token = await get_refresh_token(db, incoming_token)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )
    if token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired"
        )

    user: User | None = await db.get(User, token.user_id)

    if user:
        try:
            await delete_refresh_token(db, token)

            await delete_expired_refresh_tokens_for_user(db, user.id)

            new_access_token = create_access_token(user.id)
            new_refresh_token = await create_refresh_token(db, user.id)

            await db.commit()

            return TokensPair(
                access_token=new_access_token, refresh_token=new_refresh_token
            )

        except Exception as e:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not process token rotation. Details: {e}",
            ) from e
