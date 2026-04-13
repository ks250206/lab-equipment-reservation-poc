from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, get_token_payload, is_app_admin_from_payload, require_admin
from ..config import UserRole
from ..db import get_session
from ..models import User
from ..schemas import UserResponse, UserUpdate
from ..services.users import get_user as get_user_by_id
from ..services.users import update_user as apply_user_update

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    payload: dict = Depends(get_token_payload),
) -> UserResponse:
    role = UserRole.ADMIN if is_app_admin_from_payload(payload) else UserRole.USER
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        keycloak_id=current_user.keycloak_id,
        role=role.value,
        created_at=current_user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> list[User]:
    result = await session.execute(select(User).order_by(desc(User.created_at)))
    return list(result.scalars().all())


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    body: UserUpdate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> User:
    try:
        uuid_obj = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    user = await get_user_by_id(session, uuid_obj)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await apply_user_update(session, user, body)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
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
