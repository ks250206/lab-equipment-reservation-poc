from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..config import ReservationStatus
from ..db import get_session
from ..models import Device, Reservation, User
from ..schemas import ReservationCreate, ReservationResponse, ReservationUpdate
from ..services.reservations import check_time_overlap

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _status_str(value: ReservationStatus | str) -> str:
    if isinstance(value, str):
        return value
    return value.value


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Reservation]:
    result = await session.execute(
        select(Reservation).where(Reservation.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=ReservationResponse)
async def create_reservation(
    reservation_data: ReservationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Reservation:

    device_result = await session.execute(
        select(Device).where(Device.id == reservation_data.device_id)
    )
    device = device_result.scalar_one_or_none()

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if reservation_data.start_time >= reservation_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time",
        )

    if await check_time_overlap(
        session,
        reservation_data.device_id,
        reservation_data.start_time,
        reservation_data.end_time,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot overlaps with existing reservation",
        )

    reservation = Reservation(
        **reservation_data.model_dump(),
        user_id=current_user.id,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: str,
    reservation_data: ReservationUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Reservation:
    try:
        uuid_obj = UUID(reservation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reservation ID format",
        ) from None

    result = await session.execute(
        select(Reservation).where(
            Reservation.id == uuid_obj,
            Reservation.user_id == current_user.id,
        )
    )
    reservation = result.scalar_one_or_none()

    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    update_dict = reservation_data.model_dump(exclude_unset=True)

    new_start = update_dict.get("start_time", reservation.start_time)
    new_end = update_dict.get("end_time", reservation.end_time)
    new_status = update_dict.get("status", reservation.status)

    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time",
        )

    if _status_str(new_status) != ReservationStatus.CANCELLED.value and await check_time_overlap(
        session,
        reservation.device_id,
        new_start,
        new_end,
        exclude_reservation_id=uuid_obj,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot overlaps with existing reservation",
        )

    for key, value in update_dict.items():
        setattr(reservation, key, value)

    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(
    reservation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        uuid_obj = UUID(reservation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reservation ID format",
        ) from None

    result = await session.execute(
        select(Reservation).where(
            Reservation.id == uuid_obj,
            Reservation.user_id == current_user.id,
        )
    )
    reservation = result.scalar_one_or_none()

    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    await session.delete(reservation)
    await session.commit()
