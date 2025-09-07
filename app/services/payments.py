from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Payment, PaymentLog, PaymentStatus, User
from app.schemas.payments import PaymentCreate, PaymentFilter, PaymentUpdate


async def create_payment(
    session: AsyncSession, data: PaymentCreate, current_user: User
) -> Payment:
    # Проверяем, что получатель существует
    stmt = select(User).where(User.id == data.recipient_id)
    result = await session.execute(stmt)
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found"
        )

    payment = Payment(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        card_last4=data.card_last4,
        card_holder=data.card_holder,
        amount=data.amount,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def confirm_payment(
    session: AsyncSession, payment_id: UUID, user: User
) -> Payment:
    async with session.begin():
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
            )

        if payment.status in {PaymentStatus.PAID, PaymentStatus.CANCELED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already finalized",
            )

        # Проверка баланса отправителя
        sender_stmt = select(User).where(User.id == payment.sender_id).with_for_update()
        sender_result = await session.execute(sender_stmt)
        sender = sender_result.scalar_one()
        if sender.balance < payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance"
            )

        # Получатель
        recipient_stmt = (
            select(User).where(User.id == payment.recipient_id).with_for_update()
        )
        recipient_result = await session.execute(recipient_stmt)
        recipient = recipient_result.scalar_one()

        # Обновление статуса и балансов
        payment.status = PaymentStatus.PAID
        sender.balance -= payment.amount
        recipient.balance += payment.amount

        # Логируем изменение
        log = PaymentLog(
            payment_id=payment.id,
            performed_by=user.id,
            prev_status=PaymentStatus.CREATED,
            new_status=PaymentStatus.PAID,
            amount=payment.amount,
            note="Payment confirmed",
        )
        session.add(log)

    await session.commit()
    await session.refresh(payment)
    return payment


async def cancel_payment(
    session: AsyncSession, payment_id: UUID, user: User
) -> Payment:
    async with session.begin():
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
            )

        if payment.status in {PaymentStatus.PAID, PaymentStatus.CANCELED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already finalized",
            )

        payment.status = PaymentStatus.CANCELED

        log = PaymentLog(
            payment_id=payment.id,
            performed_by=user.id,
            prev_status=PaymentStatus.CREATED,
            new_status=PaymentStatus.CANCELED,
            amount=payment.amount,
            note="Payment canceled",
        )
        session.add(log)

    await session.commit()
    await session.refresh(payment)
    return payment


async def list_payments(session: AsyncSession, user: User, filters: PaymentFilter):
    stmt = select(Payment).where(Payment.sender_id == user.id)

    if filters.status:
        stmt = stmt.where(Payment.status == filters.status)
    if filters.min_sum:
        stmt = stmt.where(Payment.amount >= filters.min_sum)
    if filters.max_sum:
        stmt = stmt.where(Payment.amount <= filters.max_sum)

    result = await session.execute(stmt)
    payments = result.scalars().all()
    return payments


async def get_payment_by_id(
    session: AsyncSession, payment_id: UUID
) -> Optional[Payment]:
    """
    Get payment by ID.
    """
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await session.execute(stmt)
    payment = result.scalar_one_or_none()
    return payment


async def get_payment_logs(session: AsyncSession, payment_id: UUID) -> List[PaymentLog]:
    """
    Get payment logs by payment ID.
    """
    stmt = select(PaymentLog).where(PaymentLog.payment_id == payment_id)
    result = await session.execute(stmt)
    logs = list(result.scalars().all())
    return logs


async def update_payment(
    session: AsyncSession, payment_id: UUID, data: PaymentUpdate, user: User
) -> Payment:
    """
    Update payment status.
    """
    async with session.begin():
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
            )

        # Store previous status for logging
        prev_status = payment.status
        payment.status = PaymentStatus(data.status.value)

        # Log the change
        log = PaymentLog(
            payment_id=payment.id,
            performed_by=user.id,
            prev_status=prev_status,
            new_status=data.status,
            amount=payment.amount,
            note=f"Payment status updated to {data.status.value}",
        )
        session.add(log)

    await session.commit()
    await session.refresh(payment)
    return payment


async def delete_payment(session: AsyncSession, payment_id: UUID, user: User) -> bool:
    """
    Delete payment (only if it's in CREATED status).
    """
    async with session.begin():
        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
            )

        if payment.status != PaymentStatus.CREATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete payment that is not in CREATED status",
            )

        # Log the deletion
        log = PaymentLog(
            payment_id=payment.id,
            performed_by=user.id,
            prev_status=payment.status,
            new_status=payment.status,  # Same status since we're deleting
            amount=payment.amount,
            note="Payment deleted",
        )
        session.add(log)

        await session.delete(payment)

    await session.commit()
    return True
