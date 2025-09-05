from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    balance: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
