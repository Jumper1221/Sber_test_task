import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class BalanceUpdate(BaseModel):
    amount: float


class GetUserByTokenResponse(BaseModel):
    user_id: str


class UserLoginResponse(BaseModel):
    email: str
    username: str
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class UserBasicResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserLoginResponse
