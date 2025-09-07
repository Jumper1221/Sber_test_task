from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.models import User
from app.schemas.auth import UserCreate, UserLogin
from app.schemas.users import UserUpdate


async def register_user(session: AsyncSession, data: UserCreate) -> dict:
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = get_password_hash(data.password)
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


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    """
    Get user by ID.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def authenticate_user(session: AsyncSession, data: UserLogin) -> Optional[dict]:
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(data.password, user.hashed_password):
        return None

    access_token = create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


async def update_user_profile(
    session: AsyncSession, user_id: UUID, data: "UserUpdate"
) -> User:
    """
    Update user profile.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update fields if provided
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        # Check if email is already taken by another user
        email_stmt = select(User).where(User.email == data.email, User.id != user_id)
        email_result = await session.execute(email_stmt)
        existing_user = email_result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = data.email

    await session.commit()
    await session.refresh(user)
    return user


async def refresh_access_token(session: AsyncSession, refresh_token: str) -> dict:
    """
    Refresh access token using refresh token.
    """
    # Import here to avoid circular imports
    import jwt

    from app.core.config import settings

    # Decode the refresh token to get user ID
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None

    # Get user from database
    user = await get_user_by_id(session, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    access_token = create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


async def update_user_balance(
    session: AsyncSession, user_id: UUID, amount: float
) -> User:
    """
    Update user balance by adding the specified amount.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update balance
    user.balance += Decimal(str(amount))

    await session.commit()
    await session.refresh(user)
    return user
