from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import find_uniquiness_conflicts
from app.core.jwt import create_access_token, create_token_pair
from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.models import User
from app.schemas.auth import TokensPair, UserLogin, UserRegistration
from app.schemas.users import (
    LoginResponse,
    UserBasicResponse,
    UserLoginResponse,
    UserUpdate,
)


async def register(db: AsyncSession, data: UserRegistration) -> UserBasicResponse:
    stmt = (
        pg_insert(User)
        .values(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        .on_conflict_do_nothing()
        .returning(User.id)
    )

    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        conflicts = await find_uniquiness_conflicts(db, data.username, data.email)
        if not conflicts:
            conflicts = {"detail": "Конфликт уникальности"}
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflicts,
        )

    user_id = row[0]
    await db.commit()

    user = await db.get(User, user_id)
    return UserBasicResponse.model_validate(user)


# async def register_user(session: AsyncSession, data: UserCreate) -> dict:
#     stmt = select(User).where(User.email == data.email)
#     result = await session.execute(stmt)
#     existing_user = result.scalar_one_or_none()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
#         )

#     hashed_password = get_password_hash(data.password)
#     user = User(
#         email=data.email,
#         username=data.username,
#         hashed_password=hashed_password,
#     )
#     session.add(user)
#     await session.commit()
#     await session.refresh(user)

#     access_token = create_access_token(user_id=user.id)
#     return {"access_token": access_token, "token_type": "bearer"}


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
    if data.username is not None:
        user.username = data.username
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


async def login(
    username_or_email: str, password: str, db: AsyncSession
) -> LoginResponse:
    user = await db.execute(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    )

    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )
    token_pair: TokensPair = await create_token_pair(db, user.id)

    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        user=UserLoginResponse(
            email=user.email,
            username=user.username,
            id=user.id,
        ),
    )
