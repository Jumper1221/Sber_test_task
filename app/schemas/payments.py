from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatus(str, Enum):
    created = "created"
    paid = "paid"
    canceled = "canceled"


class PaymentBase(BaseModel):
    card_last4: str = Field(
        ..., min_length=4, max_length=4, description="Последние 4 цифры карты"
    )
    card_holder: str = Field(..., description="ФИО владельца карты")
    amount: Decimal = Field(
        ..., gt=0, max_digits=14, decimal_places=2, description="Сумма платежа"
    )


class PaymentCreate(PaymentBase):
    recipient_id: UUID


class PaymentRead(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    card_last4: str
    card_holder: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentUpdate(BaseModel):
    status: PaymentStatus


class PaymentFilter(BaseModel):
    status: Optional[str] = None
    min_sum: Optional[Decimal] = None
    max_sum: Optional[Decimal] = None
