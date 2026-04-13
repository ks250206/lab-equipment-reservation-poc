from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, desc, select
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
from ..models import Device, User, UserFavoriteDevice
from ..schemas import UserMeResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/me/favorites/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_my_favorite_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        did = UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        ) from None
    dev = await session.get(Device, did)
    if dev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    existing = await session.execute(
        select(UserFavoriteDevice).where(
            UserFavoriteDevice.user_id == current_user.id,
            UserFavoriteDevice.device_id == did,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(UserFavoriteDevice(user_id=current_user.id, device_id=did))
    await session.commit()


@router.delete("/me/favorites/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_my_favorite_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        did = UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        ) from None
    await session.execute(
        delete(UserFavoriteDevice).where(
            UserFavoriteDevice.user_id == current_user.id,
            UserFavoriteDevice.device_id == did,
        )
    )
    await session.commit()


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
