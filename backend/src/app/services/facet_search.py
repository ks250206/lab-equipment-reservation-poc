import uuid
from collections import Counter
from collections.abc import Sequence

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..config import DeviceStatus
from ..models import Device, Reservation, UserFavoriteDevice


def _device_search_filter(
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
) -> ColumnElement[bool] | None:
    conditions: list[ColumnElement[bool]] = []
    if q:
        search_pattern = f"%{q}%"
        conditions.append(
            or_(
                Device.name.ilike(search_pattern),
                Device.description.ilike(search_pattern),
                Device.location.ilike(search_pattern),
                Device.category.ilike(search_pattern),
            )
        )
    if category:
        conditions.append(Device.category == category)
    if location:
        conditions.append(Device.location == location)
    if status:
        conditions.append(Device.status == status)
    if not conditions:
        return None
    return and_(*conditions)


def _device_used_by_user_exists(user_id: uuid.UUID) -> ColumnElement[bool]:
    """指定ユーザーがいずれかのステータスで予約したことがある装置。"""
    subq = select(1).select_from(Reservation).where(
        Reservation.device_id == Device.id,
        Reservation.user_id == user_id,
    )
    return exists(subq)


def _device_favorited_by_user_exists(user_id: uuid.UUID) -> ColumnElement[bool]:
    subq = select(1).select_from(UserFavoriteDevice).where(
        UserFavoriteDevice.device_id == Device.id,
        UserFavoriteDevice.user_id == user_id,
    )
    return exists(subq)


def _device_list_where_clause(
    *,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    personal_user_id: uuid.UUID | None = None,
    used_by_me: bool = False,
    favorites_only: bool = False,
) -> ColumnElement[bool] | None:
    parts: list[ColumnElement[bool]] = []
    base = _device_search_filter(q=q, category=category, location=location, status=status)
    if base is not None:
        parts.append(base)
    if personal_user_id is not None:
        if used_by_me:
            parts.append(_device_used_by_user_exists(personal_user_id))
        if favorites_only:
            parts.append(_device_favorited_by_user_exists(personal_user_id))
    if not parts:
        return None
    return and_(*parts)


async def search_devices(
    session: AsyncSession,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    *,
    personal_user_id: uuid.UUID | None = None,
    used_by_me: bool = False,
    favorites_only: bool = False,
) -> Sequence[Device]:
    filt = _device_list_where_clause(
        q=q,
        category=category,
        location=location,
        status=status,
        personal_user_id=personal_user_id,
        used_by_me=used_by_me,
        favorites_only=favorites_only,
    )
    query = select(Device).order_by(Device.name.asc(), Device.id.asc())
    if filt is not None:
        query = query.where(filt)
    result = await session.execute(query)
    return result.scalars().all()


async def favorite_device_ids_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    device_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    """指定装置 ID のうち、ユーザーがお気に入りにしているもの。"""
    if not device_ids:
        return set()
    result = await session.execute(
        select(UserFavoriteDevice.device_id).where(
            UserFavoriteDevice.user_id == user_id,
            UserFavoriteDevice.device_id.in_(device_ids),
        )
    )
    return set(result.scalars().all())


async def search_devices_paginated(
    session: AsyncSession,
    *,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    personal_user_id: uuid.UUID | None = None,
    used_by_me: bool = False,
    favorites_only: bool = False,
    page: int,
    page_size: int,
) -> tuple[list[Device], int]:
    filt = _device_list_where_clause(
        q=q,
        category=category,
        location=location,
        status=status,
        personal_user_id=personal_user_id,
        used_by_me=used_by_me,
        favorites_only=favorites_only,
    )
    count_stmt = select(func.count()).select_from(Device)
    list_stmt = select(Device).order_by(Device.name.asc(), Device.id.asc())
    if filt is not None:
        count_stmt = count_stmt.where(filt)
        list_stmt = list_stmt.where(filt)
    total = int(await session.scalar(count_stmt) or 0)
    offset = (page - 1) * page_size
    list_stmt = list_stmt.offset(offset).limit(page_size)
    result = await session.execute(list_stmt)
    return list(result.scalars().all()), total


async def get_facets(
    session: AsyncSession,
    q: str | None = None,
) -> dict:
    base_query = select(Device)

    if q:
        search_pattern = f"%{q}%"
        base_query = base_query.where(
            or_(
                Device.name.ilike(search_pattern),
                Device.description.ilike(search_pattern),
                Device.location.ilike(search_pattern),
                Device.category.ilike(search_pattern),
            )
        )

    result = await session.execute(base_query)
    devices = result.scalars().all()

    categories = [d.category for d in devices if d.category]
    locations = [d.location for d in devices if d.location]
    statuses = [d.status.value for d in devices]

    facets = {
        "category": [
            {"value": value, "count": count} for value, count in Counter(categories).most_common()
        ],
        "location": [
            {"value": value, "count": count} for value, count in Counter(locations).most_common()
        ],
        "status": [
            {"value": value, "count": count} for value, count in Counter(statuses).most_common()
        ],
    }

    return facets


async def get_all_categories(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Device.category).where(Device.category.isnot(None)).distinct()
    )
    return [row[0] for row in result.all()]


async def get_all_locations(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Device.location).where(Device.location.isnot(None)).distinct()
    )
    return [row[0] for row in result.all()]
