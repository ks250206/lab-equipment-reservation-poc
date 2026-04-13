from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..config import ReservationStatus
from ..datetime_util import ensure_utc
from ..db import get_session
from ..models import Device, Reservation, User
from ..pagination import ListPageSize
from ..reservation_mapping import reservation_to_response
from ..schemas import (
    PaginatedReservationListResponse,
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from ..services.reservations import (
    check_time_overlap,
    list_reservations_for_user_paginated,
)
from ..services.reservations import (
    delete_reservation as delete_reservation_record,
)

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _status_str(value: ReservationStatus | str) -> str:
    if isinstance(value, str):
        return value
    return value.value


@router.get("", response_model=PaginatedReservationListResponse)
async def list_reservations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    device_id: str | None = Query(None, description="装置 ID で絞り込み"),
    reservation_status: str | None = Query(None, description="予約ステータスで絞り込み"),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    include_cancelled: bool = Query(
        True,
        description=(
            "ステータス未指定時: false のときキャンセル行を除く（既定 true でキャンセルも含む）"
        ),
    ),
    favorites_only: bool = Query(False, description="お気に入り登録した装置の予約に限定"),
    page: int = Query(1, ge=1, description="1 始まりのページ番号"),
    page_size: ListPageSize = Query(
        ListPageSize.FIFTY, description="1 ページあたり件数（20 / 50 / 100）"
    ),
) -> PaginatedReservationListResponse:
    if (from_ is None) != (to is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameters 'from' and 'to' must be used together",
        )
    if from_ is not None and to is not None:
        if from_ >= to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'from' must be before 'to'",
            )

    dev_uuid: UUID | None = None
    if device_id is not None:
        try:
            dev_uuid = UUID(device_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device ID format",
            ) from None
        dev_row = await session.get(Device, dev_uuid)
        if dev_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

    status_enum: ReservationStatus | None = None
    if reservation_status is not None:
        try:
            status_enum = ReservationStatus(reservation_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid reservation status: {reservation_status}",
            ) from None

    items, total = await list_reservations_for_user_paginated(
        session,
        current_user.id,
        device_id=dev_uuid,
        status_filter=status_enum,
        window_start=ensure_utc(from_) if from_ is not None else None,
        window_end=ensure_utc(to) if to is not None else None,
        include_cancelled=include_cancelled,
        favorites_only=favorites_only,
        page=page,
        page_size=int(page_size),
    )
    return PaginatedReservationListResponse(
        items=[reservation_to_response(r) for r in items],
        total=total,
        page=page,
        page_size=int(page_size),
    )


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

    payload = reservation_data.model_dump()
    start_utc = ensure_utc(payload["start_time"])
    end_utc = ensure_utc(payload["end_time"])

    if start_utc >= end_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time",
        )

    if await check_time_overlap(
        session,
        reservation_data.device_id,
        start_utc,
        end_utc,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="指定した時間帯は既存の予約と重なっています。別の時間帯を選んでください。",
        )

    reservation = Reservation(
        device_id=payload["device_id"],
        start_time=start_utc,
        end_time=end_utc,
        purpose=payload.get("purpose"),
        user_id=current_user.id,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/complete-usage", response_model=ReservationResponse)
async def complete_reservation_usage(
    reservation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Reservation:
    """確定中の予約を利用完了（completed）へ。一般 PUT では completed にできない。"""
    try:
        uuid_obj = UUID(reservation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reservation ID format",
        ) from None

    result = await session.execute(
        select(Reservation)
        .where(
            Reservation.id == uuid_obj,
            Reservation.user_id == current_user.id,
        )
        .options(selectinload(Reservation.user))
    )
    reservation = result.scalar_one_or_none()

    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if reservation.status != ReservationStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="利用完了の報告は確定（confirmed）の予約にのみ行えます。",
        )

    reservation.status = ReservationStatus.COMPLETED
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

    if reservation.status == ReservationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed reservations cannot be modified",
        )

    update_dict = reservation_data.model_dump(exclude_unset=True)

    new_start = (
        ensure_utc(update_dict["start_time"])
        if "start_time" in update_dict
        else reservation.start_time
    )
    new_end = (
        ensure_utc(update_dict["end_time"]) if "end_time" in update_dict else reservation.end_time
    )
    new_status = update_dict.get("status", reservation.status)

    if _status_str(new_status) == ReservationStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="利用完了（completed）への変更は「利用完了報告」画面の専用操作から行ってください。",
        )

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
            detail="指定した時間帯は既存の予約と重なっています。別の時間帯を選んでください。",
        )

    for key, value in update_dict.items():
        if key in ("start_time", "end_time") and isinstance(value, datetime):
            value = ensure_utc(value)
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

    try:
        await delete_reservation_record(session, reservation)
    except ValueError as e:
        detail = str(e)
        if detail == "Completed reservations cannot be deleted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        raise
