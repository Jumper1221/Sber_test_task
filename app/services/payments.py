from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_async_session

from app.models.models import Payment, PaymentLog, PaymentStatus, User
from app.schemas.payments import PaymentCreate, PaymentFilter


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
