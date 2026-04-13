import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import UserRole
from ..models import User
from ..schemas import UserUpdate


async def create_user(
    session: AsyncSession,
    keycloak_id: str,
    email: str,
    name: str | None = None,
    role: UserRole = UserRole.USER,
) -> User:
    user = User(
        keycloak_id=keycloak_id,
        email=email,
        name=name,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_users(
    session: AsyncSession,
) -> Sequence[User]:
    result = await session.execute(select(User))
    return result.scalars().all()


async def update_user(
    session: AsyncSession,
    user: User,
    user_data: UserUpdate,
) -> User:
    if user_data.name is not None:
        user.name = user_data.name
    await session.commit()
    await session.refresh(user)
    return user
