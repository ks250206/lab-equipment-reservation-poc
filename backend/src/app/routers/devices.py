import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_admin
from ..config import DeviceStatus
from ..db import get_session
from ..models import Device
from ..schemas import DeviceCreate, DeviceResponse, DeviceUpdate
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
    search_devices,
)
from ..services import (
    update_device as update_device_service,
)

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    q: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    location: str | None = Query(None, description="Filter by location"),
    status: DeviceStatus | None = Query(None, description="Filter by status"),
    session: AsyncSession = Depends(get_session),
) -> list[Device]:
    return list(
        await search_devices(
            session,
            q=q,
            category=category,
            location=location,
            status=status,
        )
    )


@router.get("/facets")
async def get_device_facets(
    q: str | None = Query(None, description="Search query for facets"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_facets(session, q=q)


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
    admin: Device = Depends(require_admin),
) -> Device:
    return await create_device_service(session, device_data)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    session: AsyncSession = Depends(get_session),
    admin: Device = Depends(require_admin),
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
    return await update_device_service(session, device, device_data)


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    admin: Device = Depends(require_admin),
) -> None:
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
