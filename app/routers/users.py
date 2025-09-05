from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.users import UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user=Depends(get_current_user)):
    return current_user
