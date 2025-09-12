from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.jwt import decode_access_token
from app.models.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008 для FastAPI это нормальная реализация
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Decode access token and return the User model instance from DB."""
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("sub", None)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload"
        ) from None

    # token stores user id as string (uuid). Convert to UUID and load user.
    try:
        import uuid as _uuid

        user_uuid = _uuid.UUID(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token subject"
        ) from None

    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        ) from None

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


# async def add_jti_to_blocklist(jti: str, exp_time: datetime):
#     """Add a JWT ID to the blocklist."""
#     now = datetime.now(timezone.utc)
#     ttl = round((exp_time - now).total_seconds())
#     if ttl > 0:
#         await redis_client.setex(jti, ttl, "blocked")


# async def check_blocklist(jti: str) -> bool:
#     """Check if a JWT ID is in the blocklist."""
#     return await redis_client.get(jti) is not None


async def find_uniquiness_conflicts(
    db: AsyncSession, username: str, email: str
) -> dict[str, str]:
    """Check if the username, email, or phone already exists in the database."""

    query = (
        select(User.username, User.email)
        .where(
            or_(
                func.lower(User.username) == func.lower(username),
                func.lower(User.email) == func.lower(email),
            )
        )
        .limit(5)
    )

    rows = (await db.execute(query)).all()
    problems: dict[str, str] = {}
    for n, e in rows:
        if n.lower() == username.lower():
            problems["username"] = "уже занят"
        if e == email:
            problems["email"] = "уже занята"
    return problems
