from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    get_current_user,
    get_token_payload,
    is_app_admin_from_payload,
    me_profile_fields_from_payload,
    require_admin,
)
from ..config import UserRole
from ..db import get_session
from ..models import User
from ..schemas import UserMeResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    payload: dict = Depends(get_token_payload),
) -> UserMeResponse:
    email, disp_name = me_profile_fields_from_payload(payload, current_user.keycloak_id)
    role = UserRole.ADMIN.value if is_app_admin_from_payload(payload) else UserRole.USER.value
    return UserMeResponse(
        id=current_user.id,
        keycloak_id=current_user.keycloak_id,
        created_at=current_user.created_at,
        email=email,
        name=disp_name,
        role=role,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> list[User]:
    result = await session.execute(select(User).order_by(desc(User.created_at)))
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> User:
    try:
        uuid_obj = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    result = await session.execute(select(User).where(User.id == uuid_obj))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
