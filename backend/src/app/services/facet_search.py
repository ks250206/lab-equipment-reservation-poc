from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..config import DeviceStatus, ReservationStatus
from ..datetime_util import ensure_utc
from ..models import Device, Reservation, User


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


def _device_reservation_presence_condition(
    *,
    reservation_user: str | None,
    reservation_from: datetime | None,
    reservation_to: datetime | None,
) -> ColumnElement[bool] | None:
    """非キャンセル予約で、ユーザー名一致・期間交差の条件に合う装置を EXISTS で絞る。"""
    user_s = (reservation_user or "").strip()
    has_user = bool(user_s)
    has_window = False
    win_start: datetime | None = None
    win_end: datetime | None = None
    if reservation_from is not None and reservation_to is not None:
        win_start = ensure_utc(reservation_from)
        win_end = ensure_utc(reservation_to)
        if win_start < win_end:
            has_window = True
    if not has_user and not has_window:
        return None

    conds: list[ColumnElement[bool]] = [
        Reservation.device_id == Device.id,
        Reservation.status != ReservationStatus.CANCELLED,
    ]
    if has_window and win_start is not None and win_end is not None:
        conds.append(Reservation.start_time < win_end)
        conds.append(Reservation.end_time > win_start)
    if has_user:
        pat = f"%{user_s}%"
        conds.append(or_(User.name.ilike(pat), User.email.ilike(pat)))

    subq = (
        select(1)
        .select_from(Reservation)
        .join(User, User.id == Reservation.user_id)
        .where(and_(*conds))
    )
    return exists(subq)


def _device_list_where_clause(
    *,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    reservation_user: str | None = None,
    reservation_from: datetime | None = None,
    reservation_to: datetime | None = None,
) -> ColumnElement[bool] | None:
    parts: list[ColumnElement[bool]] = []
    base = _device_search_filter(q=q, category=category, location=location, status=status)
    if base is not None:
        parts.append(base)
    res = _device_reservation_presence_condition(
        reservation_user=reservation_user,
        reservation_from=reservation_from,
        reservation_to=reservation_to,
    )
    if res is not None:
        parts.append(res)
    if not parts:
        return None
    return and_(*parts)


async def search_devices(
    session: AsyncSession,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    reservation_user: str | None = None,
    reservation_from: datetime | None = None,
    reservation_to: datetime | None = None,
) -> Sequence[Device]:
    filt = _device_list_where_clause(
        q=q,
        category=category,
        location=location,
        status=status,
        reservation_user=reservation_user,
        reservation_from=reservation_from,
        reservation_to=reservation_to,
    )
    query = select(Device).order_by(Device.name.asc(), Device.id.asc())
    if filt is not None:
        query = query.where(filt)
    result = await session.execute(query)
    return result.scalars().all()


async def search_devices_paginated(
    session: AsyncSession,
    *,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
    reservation_user: str | None = None,
    reservation_from: datetime | None = None,
    reservation_to: datetime | None = None,
    page: int,
    page_size: int,
) -> tuple[list[Device], int]:
    filt = _device_list_where_clause(
        q=q,
        category=category,
        location=location,
        status=status,
        reservation_user=reservation_user,
        reservation_from=reservation_from,
        reservation_to=reservation_to,
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
