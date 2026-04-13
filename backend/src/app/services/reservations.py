import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import ReservationStatus
from ..datetime_util import ensure_utc
from ..models import Reservation, UserFavoriteDevice
from ..schemas import ReservationCreate, ReservationUpdate


async def create_reservation(
    session: AsyncSession,
    reservation_data: ReservationCreate,
    user_id: uuid.UUID,
) -> Reservation:
    data = reservation_data.model_dump()
    reservation = Reservation(
        device_id=data["device_id"],
        user_id=user_id,
        start_time=ensure_utc(data["start_time"]),
        end_time=ensure_utc(data["end_time"]),
        purpose=data.get("purpose"),
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


async def get_reservation(
    session: AsyncSession,
    reservation_id: uuid.UUID,
) -> Reservation | None:
    result = await session.execute(select(Reservation).where(Reservation.id == reservation_id))
    return result.scalar_one_or_none()


async def get_reservations_by_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Sequence[Reservation]:
    result = await session.execute(select(Reservation).where(Reservation.user_id == user_id))
    return result.scalars().all()


async def get_reservations_by_device(
    session: AsyncSession,
    device_id: uuid.UUID,
) -> Sequence[Reservation]:
    result = await session.execute(select(Reservation).where(Reservation.device_id == device_id))
    return result.scalars().all()


def _reservation_device_window_where(
    device_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
    *,
    mine_user_id: uuid.UUID | None,
    status_filter: ReservationStatus | None,
    viewer_user_id: uuid.UUID,
    hide_all_cancelled: bool,
) -> tuple[Any, datetime, datetime]:
    """窓と重なる予約行の WHERE 句（`window_start` < `window_end` を前提）。

    - カレンダー（hide_all_cancelled）: キャンセルは常に除外。
    - リスト: 他人のキャンセルは除外。閲覧者本人のキャンセルは（絞り込み次第で）表示。
    """
    ws = ensure_utc(window_start)
    we = ensure_utc(window_end)
    conds: list[Any] = [
        Reservation.device_id == device_id,
        Reservation.end_time > ws,
        Reservation.start_time < we,
    ]
    if mine_user_id is not None:
        conds.append(Reservation.user_id == mine_user_id)

    if hide_all_cancelled:
        conds.append(Reservation.status != ReservationStatus.CANCELLED)
    elif status_filter is not None:
        if status_filter == ReservationStatus.CANCELLED:
            conds.append(Reservation.status == ReservationStatus.CANCELLED)
            conds.append(Reservation.user_id == viewer_user_id)
        else:
            conds.append(Reservation.status == status_filter)
    else:
        # 他人のキャンセルは出さない。閲覧者本人のキャンセルは include_cancelled に関わらず同じ。
        conds.append(
            or_(
                Reservation.status != ReservationStatus.CANCELLED,
                Reservation.user_id == viewer_user_id,
            )
        )

    return and_(*conds), ws, we


async def list_reservations_for_device_in_window(
    session: AsyncSession,
    device_id: uuid.UUID,
    *,
    window_start: datetime,
    window_end: datetime,
    include_cancelled: bool = False,
    mine_user_id: uuid.UUID | None = None,
    status_filter: ReservationStatus | None = None,
    viewer_user_id: uuid.UUID,
    hide_all_cancelled: bool = False,
) -> Sequence[Reservation]:
    """装置の予約を時刻窓で取得（窓と重なる行）。`window_start` < `window_end` を前提とする。"""
    _ = include_cancelled
    where_expr, _ws, _we = _reservation_device_window_where(
        device_id,
        window_start,
        window_end,
        mine_user_id=mine_user_id,
        status_filter=status_filter,
        viewer_user_id=viewer_user_id,
        hide_all_cancelled=hide_all_cancelled,
    )
    q = (
        select(Reservation)
        .where(where_expr)
        .options(selectinload(Reservation.user))
        .order_by(Reservation.start_time.asc())
    )
    result = await session.execute(q)
    return result.scalars().all()


async def list_reservations_for_device_in_window_paginated(
    session: AsyncSession,
    device_id: uuid.UUID,
    *,
    window_start: datetime,
    window_end: datetime,
    include_cancelled: bool = False,
    mine_user_id: uuid.UUID | None = None,
    status_filter: ReservationStatus | None = None,
    page: int,
    page_size: int,
    viewer_user_id: uuid.UUID,
    hide_all_cancelled: bool = False,
) -> tuple[list[Reservation], int]:
    _ = include_cancelled
    where_expr, _ws, _we = _reservation_device_window_where(
        device_id,
        window_start,
        window_end,
        mine_user_id=mine_user_id,
        status_filter=status_filter,
        viewer_user_id=viewer_user_id,
        hide_all_cancelled=hide_all_cancelled,
    )
    count_stmt = select(func.count()).select_from(Reservation).where(where_expr)
    total = int(await session.scalar(count_stmt) or 0)
    offset = (page - 1) * page_size
    list_stmt = (
        select(Reservation)
        .where(where_expr)
        .options(selectinload(Reservation.user))
        .order_by(Reservation.start_time.asc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(list_stmt)
    return list(result.scalars().all()), total


async def list_reservations_for_user_paginated(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    device_id: uuid.UUID | None,
    status_filter: ReservationStatus | None,
    window_start: datetime | None,
    window_end: datetime | None,
    include_cancelled: bool,
    favorites_only: bool = False,
    page: int,
    page_size: int,
) -> tuple[list[Reservation], int]:
    """ログインユーザーの予約をページング。`window_*` は両方指定時のみ窓で重なり判定。"""
    conds: list[Any] = [Reservation.user_id == user_id]

    if device_id is not None:
        conds.append(Reservation.device_id == device_id)

    if favorites_only:
        fav_subq = select(1).select_from(UserFavoriteDevice).where(
            UserFavoriteDevice.user_id == user_id,
            UserFavoriteDevice.device_id == Reservation.device_id,
        )
        conds.append(exists(fav_subq))

    if status_filter is not None:
        conds.append(Reservation.status == status_filter)
    elif not include_cancelled:
        conds.append(Reservation.status != ReservationStatus.CANCELLED)

    if window_start is not None and window_end is not None:
        ws = ensure_utc(window_start)
        we = ensure_utc(window_end)
        conds.extend(
            [
                Reservation.end_time > ws,
                Reservation.start_time < we,
            ]
        )

    where_expr = and_(*conds)
    count_stmt = select(func.count()).select_from(Reservation).where(where_expr)
    total = int(await session.scalar(count_stmt) or 0)
    offset = (page - 1) * page_size
    list_stmt = (
        select(Reservation)
        .where(where_expr)
        .options(selectinload(Reservation.user))
        .order_by(Reservation.start_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(list_stmt)
    return list(result.scalars().all()), total


async def update_reservation(
    session: AsyncSession,
    reservation: Reservation,
    reservation_data: ReservationUpdate,
) -> Reservation:
    update_dict = reservation_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if key in ("start_time", "end_time") and isinstance(value, datetime):
            value = ensure_utc(value)
        setattr(reservation, key, value)
    await session.commit()
    await session.refresh(reservation)
    return reservation


async def delete_reservation(
    session: AsyncSession,
    reservation: Reservation,
) -> None:
    if reservation.status == ReservationStatus.COMPLETED:
        msg = "Completed reservations cannot be deleted"
        raise ValueError(msg)
    if reservation.status == ReservationStatus.CONFIRMED:
        reservation.status = ReservationStatus.CANCELLED
        await session.commit()
        await session.refresh(reservation)
        return
    if reservation.status == ReservationStatus.CANCELLED:
        await session.commit()
        return


async def check_time_overlap(
    session: AsyncSession,
    device_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: uuid.UUID | None = None,
) -> bool:
    start_time = ensure_utc(start_time)
    end_time = ensure_utc(end_time)
    query = select(Reservation).where(
        and_(
            Reservation.device_id == device_id,
            Reservation.status != ReservationStatus.CANCELLED,
            Reservation.start_time < end_time,
            Reservation.end_time > start_time,
        )
    )
    if exclude_reservation_id:
        query = query.where(Reservation.id != exclude_reservation_id)

    result = await session.execute(query)
    return result.scalar_one_or_none() is not None
