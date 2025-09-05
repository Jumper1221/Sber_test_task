from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_user
from app.schemas.payments import (
    PaymentCreate,
    PaymentFilter,
    PaymentRead,
)
from app.services.payments import (
    cancel_payment,
    confirm_payment,
    create_payment,
    list_payments,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create(
    data: PaymentCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    return await create_payment(session=session, data=data, current_user=current_user)


@router.post("/{payment_id}/confirm", response_model=PaymentRead)
async def confirm(
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    return await confirm_payment(
        session=session, payment_id=payment_id, user=current_user
    )


@router.post("/{payment_id}/cancel", response_model=PaymentRead)
async def cancel(
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    return await cancel_payment(
        session=session, payment_id=payment_id, user=current_user
    )


@router.get("/", response_model=List[PaymentRead])
async def get_payments(
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу"),
    min_sum: Optional[float] = Query(None, description="Мин. сумма"),
    max_sum: Optional[float] = Query(None, description="Макс. сумма"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    filters = PaymentFilter(status=status_filter, min_sum=min_sum, max_sum=max_sum)
    return await list_payments(session=session, user=current_user, filters=filters)
