import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Device
from ..schemas import DeviceCreate, DeviceUpdate
from ..storage.s3_device_images import delete_device_image_object


async def create_device(
    session: AsyncSession,
    device_data: DeviceCreate,
) -> Device:
    device = Device(**device_data.model_dump())
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def get_device(
    session: AsyncSession,
    device_id: uuid.UUID,
) -> Device | None:
    result = await session.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none()


async def get_devices(
    session: AsyncSession,
) -> Sequence[Device]:
    result = await session.execute(select(Device))
    return result.scalars().all()


async def update_device(
    session: AsyncSession,
    device: Device,
    device_data: DeviceUpdate,
) -> Device:
    update_dict = device_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(device, key, value)
    device.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(device)
    return device


async def delete_device(
    session: AsyncSession,
    device: Device,
) -> None:
    delete_device_image_object(object_key=device.image_object_key)
    await session.delete(device)
    await session.commit()
