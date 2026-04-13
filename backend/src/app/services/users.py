import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


async def create_user(
    session: AsyncSession,
    keycloak_id: str,
) -> User:
    user = User(
        keycloak_id=keycloak_id,
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
