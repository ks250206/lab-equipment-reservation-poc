import uuid
from datetime import UTC, datetime, timedelta
from enum import IntEnum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_admin
from ..config import DeviceStatus
from ..db import get_session
from ..models import Device, Reservation, User
from ..schemas import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    PaginatedDeviceListResponse,
    PaginatedReservationListResponse,
    ReservationResponse,
)
from ..services import (
    create_device as create_device_service,
)
from ..services import (
    delete_device as delete_device_service,
)
from ..services import (
    get_device as get_device_service,
)
from ..services import (
    get_facets,
    search_devices_paginated,
)
from ..services import (
    update_device as update_device_service,
)
from ..services.reservations import list_reservations_for_device_in_window_paginated

router = APIRouter(prefix="/api/devices", tags=["devices"])

_DEFAULT_WINDOW = timedelta(days=183)


def _reservation_to_response(row: Reservation) -> ReservationResponse:
    u = row.user
    status_val = row.status.value if hasattr(row.status, "value") else str(row.status)
    return ReservationResponse(
        id=row.id,
        device_id=row.device_id,
        user_id=row.user_id,
        start_time=row.start_time,
        end_time=row.end_time,
        purpose=row.purpose,
        status=status_val,
        created_at=row.created_at,
        user_name=u.name if u is not None else None,
        user_email=u.email if u is not None else None,
    )


class ListPageSize(IntEnum):
    """一覧 API の page_size（クエリ文字列からの解釈用）。"""

    TWENTY = 20
    FIFTY = 50
    HUNDRED = 100


@router.get("", response_model=PaginatedDeviceListResponse)
async def list_devices(
    q: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    location: str | None = Query(None, description="Filter by location"),
    status: DeviceStatus | None = Query(None, description="Filter by status"),
    reservation_user: str | None = Query(
        None, description="予約ユーザーの氏名・メールに部分一致する予約を持つ装置に限定"
    ),
    reservation_from: datetime | None = Query(
        None, description="予約期間フィルタ開始（UTC 解釈）。`reservation_to` と併用"
    ),
    reservation_to: datetime | None = Query(
        None, description="予約期間フィルタ終了（UTC 解釈）。`reservation_from` と併用"
    ),
    page: int = Query(1, ge=1, description="1 始まりのページ番号"),
    page_size: ListPageSize = Query(
        ListPageSize.FIFTY, description="1 ページあたり件数（20 / 50 / 100）"
    ),
    session: AsyncSession = Depends(get_session),
) -> PaginatedDeviceListResponse:
    items, total = await search_devices_paginated(
        session,
        q=q,
        category=category,
        location=location,
        status=status,
        reservation_user=reservation_user,
        reservation_from=reservation_from,
        reservation_to=reservation_to,
        page=page,
        page_size=int(page_size),
    )
    return PaginatedDeviceListResponse(
        items=[DeviceResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=int(page_size),
    )


@router.get("/facets")
async def get_device_facets(
    q: str | None = Query(None, description="Search query for facets"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_facets(session, q=q)


@router.get("/{device_id}/reservations", response_model=PaginatedReservationListResponse)
async def list_device_reservations(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    include_cancelled: bool = Query(False),
    page: int = Query(1, ge=1, description="1 始まりのページ番号"),
    page_size: ListPageSize = Query(
        ListPageSize.FIFTY, description="1 ページあたり件数（20 / 50 / 100）"
    ),
) -> PaginatedReservationListResponse:
    _ = current_user
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if (from_ is None) != (to is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameters 'from' and 'to' must be used together",
        )

    now = datetime.now(UTC)
    if from_ is not None and to is not None:
        range_start, range_end = from_, to
        if range_start >= range_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'from' must be before 'to'",
            )
    else:
        range_start = now - _DEFAULT_WINDOW
        range_end = now + _DEFAULT_WINDOW

    items, total = await list_reservations_for_device_in_window_paginated(
        session,
        uuid_obj,
        window_start=range_start,
        window_end=range_end,
        include_cancelled=include_cancelled,
        page=page,
        page_size=int(page_size),
    )
    return PaginatedReservationListResponse(
        items=[_reservation_to_response(r) for r in items],
        total=total,
        page=page,
        page_size=int(page_size),
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> Device:
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return device


@router.post("", response_model=DeviceResponse)
async def create_device(
    device_data: DeviceCreate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> Device:
    _ = admin
    return await create_device_service(session, device_data)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> Device:
    _ = admin
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return await update_device_service(session, device, device_data)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> None:
    _ = admin
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    await delete_device_service(session, device)
