import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import Response

from ..auth import get_current_user, get_optional_current_user, require_admin
from ..config import DeviceStatus, ReservationStatus, get_settings
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
    favorite_device_ids_for_user,
    get_facets,
    search_devices_paginated,
)
from ..services import (
    get_device as get_device_service,
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
    device_status: DeviceStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    used_by_me: bool = Query(False, description="ログインユーザーが一度でも予約した装置に限定"),
    favorites_only: bool = Query(False, description="ログインユーザーがお気に入りの装置に限定"),
    page: int = Query(1, ge=1, description="1 始まりのページ番号"),
    page_size: ListPageSize = Query(
        ListPageSize.FIFTY, description="1 ページあたり件数（20 / 50 / 100）"
    ),
    session: AsyncSession = Depends(get_session),
    optional_user: User | None = Depends(get_optional_current_user),
) -> PaginatedDeviceListResponse:
    if (used_by_me or favorites_only) and optional_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "used_by_me および favorites_only にはログイン（Authorization: Bearer）が必要です"
            ),
        )
    personal_id = optional_user.id if optional_user is not None else None
    need_personal_clause = used_by_me or favorites_only
    items, total = await search_devices_paginated(
        session,
        q=q,
        category=category,
        location=location,
        status=device_status,
        personal_user_id=personal_id if need_personal_clause else None,
        used_by_me=used_by_me,
        favorites_only=favorites_only,
        page=page,
        page_size=int(page_size),
    )
    fav_ids: set[uuid.UUID] = set()
    if optional_user is not None and items:
        fav_ids = await favorite_device_ids_for_user(
            session, optional_user.id, [d.id for d in items]
        )
    return PaginatedDeviceListResponse(
        items=[device_to_response(d, is_favorite=(d.id in fav_ids)) for d in items],
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
    calendar_mode: bool = Query(
        False,
        description="カレンダー用: キャンセル済みを閲覧者・他人問わず常に除外",
    ),
    mine_only: bool = Query(False, description="ログインユーザーの予約に限定"),
    reservation_status: ReservationStatus | None = Query(
        None, description="予約ステータスで絞り込み（指定時は include_cancelled より優先）"
    ),
    page: int = Query(1, ge=1, description="1 始まりのページ番号"),
    page_size: ListPageSize = Query(
        ListPageSize.FIFTY, description="1 ページあたり件数（20 / 50 / 100）"
    ),
) -> PaginatedReservationListResponse:
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
        mine_user_id=current_user.id if mine_only else None,
        status_filter=reservation_status,
        page=page,
        page_size=int(page_size),
        viewer_user_id=current_user.id,
        hide_all_cancelled=calendar_mode,
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
    optional_user: User | None = Depends(get_optional_current_user),
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
    is_fav = False
    if optional_user is not None:
        favs = await favorite_device_ids_for_user(session, optional_user.id, [device.id])
        is_fav = device.id in favs
    return device_to_response(device, is_favorite=is_fav)


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
