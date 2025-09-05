from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.schemas.auth import Token, UserCreate, UserLogin
from app.services.auth import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate, session: AsyncSession = Depends(get_async_session)
):
    return await register_user(session=session, data=data)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, session: AsyncSession = Depends(get_async_session)):
    user = await authenticate_user(session=session, data=data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return user
