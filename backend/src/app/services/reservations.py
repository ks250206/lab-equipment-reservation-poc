import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ReservationStatus
from ..datetime_util import ensure_utc
from ..models import Reservation
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
    await session.delete(reservation)
    await session.commit()


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
