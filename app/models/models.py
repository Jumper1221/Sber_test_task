# app/models/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.token import RefreshToken
    from app.models.verification_code import VerificationCode


# Recommended naming convention for Alembic migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)


class PaymentStatus(enum.Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELED = "canceled"


class User(Base):
    """
    Пользователь системы.
    Хранит хеш пароля и баланс (для внутренних переводов/начислений).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), default=True
    )
    is_verified_email: Mapped[bool] = mapped_column(default=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Отношения
    payments_sent: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="sender",
        foreign_keys="[Payment.sender_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments_received: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="recipient",
        foreign_keys="[Payment.recipient_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    performed_logs: Mapped[List["PaymentLog"]] = relationship(
        "PaymentLog",
        back_populates="performed_by_user",
        foreign_keys="[PaymentLog.performed_by]",
        lazy="selectin",
    )

    verification_codes: Mapped[list["VerificationCode"]] = relationship(
        "VerificationCode", back_populates="user", cascade="all, delete-orphan"
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Payment(Base):
    """
    Модель платежа.
    - id: UUID платежа (уникально).
    - sender_id / recipient_id: внешние ключи на пользователей.
    - card_last4: 4 последние цифры карты (строка из 4 символов).
    - card_holder: ФИО владельца карты.
    - amount: сумма платежа (положительная).
    - status: текущее состояние платежа.
    - created_at / updated_at: метки времени.
    - version: поле для optimistic concurrency control (mapper_args).
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    card_holder: Mapped[str] = mapped_column(String(255), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        server_default=PaymentStatus.CREATED.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Поле для optimistic locking — SQLAlchemy будет поддерживать version_id_col
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )

    # Отношения
    sender: Mapped["User"] = relationship(
        "User",
        back_populates="payments_sent",
        foreign_keys=[sender_id],
        lazy="joined",
    )
    recipient: Mapped["User"] = relationship(
        "User",
        back_populates="payments_received",
        foreign_keys=[recipient_id],
        lazy="joined",
    )

    logs: Mapped[List["PaymentLog"]] = relationship(
        "PaymentLog",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __mapper_args__ = {
        "version_id_col": version,
        # опционально можно настроить "version_id_generator" при необходимости
    }

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_payments_amount_positive"),
        CheckConstraint("char_length(card_last4) = 4", name="chk_card_last4_len"),
        Index("ix_payments_sender_created_at", "sender_id", "created_at"),
    )


class PaymentLog(Base):
    """
    Аудит изменений статуса платежа.
    Хранит who, when, previous/new статусы и дополнительные заметки.
    Это позволяет в будущем просматривать историю и отлаживать операции.
    """

    __tablename__ = "payment_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prev_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
    )
    new_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
    )

    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Отношения
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="logs", lazy="joined"
    )
    performed_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="performed_logs", lazy="joined"
    )

    __table_args__ = (
        Index("ix_payment_logs_payment_id_created_at", "payment_id", "created_at"),
    )
