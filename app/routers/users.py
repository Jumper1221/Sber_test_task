from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_active_user, get_current_user
from app.schemas.users import BalanceUpdate, UserRead, UserUpdate
from app.services.auth import update_user_balance, update_user_profile

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_me(
    data: UserUpdate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_user_profile(
        session=session, user_id=current_user.id, data=data
    )


@router.get("/me/balance", response_model=dict)
async def get_balance(current_user=Depends(get_current_user)):
    """
    Get current user's balance.
    """
    return {"balance": current_user.balance}


@router.post("/me/balance", response_model=UserRead, status_code=status.HTTP_200_OK)
async def update_balance(
    data: BalanceUpdate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_user_balance(
        session=session, user_id=current_user.id, amount=data.amount
    )
