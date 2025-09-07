import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    balance: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class BalanceUpdate(BaseModel):
    amount: float


class GetUserByTokenResponse(BaseModel):
    user_id: str


class UserLoginResponse(BaseModel):
    email: str
    username: str
    id: uuid.UUID

    class Config:
        from_attributes = True


class UserBasicResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserLoginResponse
