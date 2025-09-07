from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.jwt import update_tokens_pair
from app.schemas.auth import (
    RefreshTokenRequest,
    TokensPair,
    UserLogin,
    UserRegistration,
)
from app.schemas.users import LoginResponse, UserBasicResponse
from app.services.auth import login, register

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserBasicResponse)
async def register_endpoint(
    user_data: UserRegistration, session: AsyncSession = Depends(get_async_session)
):
    """Endpoint for user registration.

    Args:
        user_data (UserRegistration): The data for the new user.
        session (AsyncSession): The database session."""

    response: UserBasicResponse = await register(session, user_data)

    return response


# @router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
# async def register(
#     data: UserCreate, session: AsyncSession = Depends(get_async_session)
# ):
#     return await register_user(session=session, data=data)


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    data: UserLogin, session: AsyncSession = Depends(get_async_session)
):
    user = await login(
        username_or_email=str(data.email), password=data.password, db=session
    )
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


@router.post("/refresh", response_model=TokensPair)
async def refresh_token(
    data: RefreshTokenRequest, session: AsyncSession = Depends(get_async_session)
):
    return await update_tokens_pair(db=session, incoming_token=data.refresh_token)
