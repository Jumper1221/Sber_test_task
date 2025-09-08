from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_user
from app.schemas.payments import (
    PaymentCreate,
    PaymentFilter,
    PaymentRead,
    PaymentUpdate,
)
from app.services.payments import (
    cancel_payment,
    confirm_payment,
    create_payment,
    delete_payment,
    get_payment_by_id,
    get_payment_logs,
    get_payments_by_user_id,
    list_payments,
    update_payment,
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
    filters = PaymentFilter(
        status=status_filter,
        min_sum=Decimal(str(min_sum)) if min_sum is not None else None,
        max_sum=Decimal(str(max_sum)) if max_sum is not None else None,
    )
    return await list_payments(session=session, user=current_user, filters=filters)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    payment = await get_payment_by_id(session=session, payment_id=payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    # Check if user is authorized to view this payment
    if payment.sender_id != current_user.id and payment.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment",
        )
    return payment


@router.put("/{payment_id}", response_model=PaymentRead)
async def update_payment_status(
    data: PaymentUpdate,
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    payment = await get_payment_by_id(session=session, payment_id=payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    # Check if user is authorized to update this payment
    if payment.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this payment",
        )
    return await update_payment(
        session=session, payment_id=payment_id, data=data, user=current_user
    )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_endpoint(
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    payment = await get_payment_by_id(session=session, payment_id=payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    # Check if user is authorized to delete this payment
    if payment.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this payment",
        )
    await delete_payment(session=session, payment_id=payment_id, user=current_user)
    return


@router.get("/{payment_id}/logs", response_model=List[dict])
async def get_logs(
    payment_id: UUID = Path(..., description="ID платежа"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    payment = await get_payment_by_id(session=session, payment_id=payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    # Check if user is authorized to view logs for this payment
    if payment.sender_id != current_user.id and payment.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view logs for this payment",
        )
    logs = await get_payment_logs(session=session, payment_id=payment_id)
    # Convert logs to dict format for response
    return [
        {
            "id": str(log.id),
            "prev_status": log.prev_status.value,
            "new_status": log.new_status.value,
            "amount": str(log.amount) if log.amount else None,
            "note": log.note,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/user/{user_id}", response_model=List[PaymentRead])
async def get_payments_for_user(
    user_id: UUID = Path(..., description="ID пользователя"),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user),
):
    """
    Get all payments for a given user ID.
    Only the user themselves can access this information.
    """
    payments = await get_payments_by_user_id(
        session=session, user_id=user_id, current_user=current_user
    )
    return payments
