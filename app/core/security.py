from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt  # pyjwt

from app.core.config import settings


def create_access_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Генерация JWT access токена.
    """
    to_encode = {"sub": str(user_id)}
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt
