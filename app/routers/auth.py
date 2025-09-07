from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.schemas.auth import RefreshTokenRequest, Token, UserCreate, UserLogin
from app.services.auth import authenticate_user, refresh_access_token, register_user

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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    Logout endpoint - in a stateless JWT implementation, this would typically
    just return a success response as the client would discard the token.
    In a stateful implementation, this would invalidate the token on the server side.
    """
    return


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest, session: AsyncSession = Depends(get_async_session)
):
    return await refresh_access_token(session=session, refresh_token=data.refresh_token)
