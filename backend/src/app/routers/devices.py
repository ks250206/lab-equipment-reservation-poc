import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from ..auth import get_current_user, require_admin
from ..config import DeviceStatus, get_settings
from ..db import get_session
from ..models import User
from ..pagination import ListPageSize
from ..reservation_mapping import reservation_to_response
from ..schemas import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    PaginatedDeviceListResponse,
    PaginatedReservationListResponse,
    device_to_response,
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
from ..services.device_image_bytes import validate_device_image_bytes
from ..services.reservations import list_reservations_for_device_in_window_paginated
from ..storage.s3_device_images import (
    delete_device_image_object,
    get_device_image_bytes,
    put_device_image_object,
)

router = APIRouter(prefix="/api/devices", tags=["devices"])

_DEFAULT_WINDOW = timedelta(days=183)


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
        items=[device_to_response(d) for d in items],
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
        items=[reservation_to_response(r) for r in items],
        total=total,
        page=page,
        page_size=int(page_size),
    )


@router.get("/{device_id}/image")
async def stream_device_image(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        ) from None

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    if not device.image_object_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device has no image",
        )
    try:
        body, content_type = await asyncio.to_thread(
            get_device_image_bytes,
            object_key=device.image_object_key,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read image: {e!s}",
        ) from e
    return Response(content=body, media_type=content_type)


@router.post("/{device_id}/image", response_model=DeviceResponse)
async def upload_device_image(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
    file: UploadFile = File(..., description="PNG または JPEG"),
) -> DeviceResponse:
    _ = admin
    try:
        uuid_obj = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        ) from None

    device = await get_device_service(session, uuid_obj)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    max_b = get_settings().device_image_max_bytes
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(65_536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_b:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"画像サイズが上限（{max_b} バイト）を超えています",
            )
        parts.append(chunk)
    raw = b"".join(parts)
    try:
        content_type = validate_device_image_bytes(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    old_key = device.image_object_key
    try:
        new_key = await asyncio.to_thread(
            put_device_image_object,
            device_id=device.id,
            body=raw,
            content_type=content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to store image: {e!s}",
        ) from e

    await asyncio.to_thread(delete_device_image_object, object_key=old_key)
    device.image_object_key = new_key
    device.image_content_type = content_type
    await session.commit()
    await session.refresh(device)
    return device_to_response(device)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeviceResponse:
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
    return device_to_response(device)


@router.post("", response_model=DeviceResponse)
async def create_device(
    device_data: DeviceCreate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> DeviceResponse:
    _ = admin
    created = await create_device_service(session, device_data)
    return device_to_response(created)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> DeviceResponse:
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
    updated = await update_device_service(session, device, device_data)
    return device_to_response(updated)


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
