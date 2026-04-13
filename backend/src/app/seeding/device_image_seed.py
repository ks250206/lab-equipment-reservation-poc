"""開発シード: 各装置に最小 PNG を MinIO に投入する。"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import Device
from ..services.device_image_bytes import validate_device_image_bytes
from ..storage.s3_device_images import (
    delete_device_image_object,
    ensure_device_images_bucket,
    put_device_image_object,
)
from .dev_seed import SEED_DEVICE_IDS

logger = logging.getLogger(__name__)

# 1x1 透明 PNG（極小）
_MINI_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def mini_png_bytes() -> bytes:
    return base64.b64decode(_MINI_PNG_B64)


async def seed_device_images_after_devices(
    factory: async_sessionmaker[AsyncSession],
    *,
    device_ids: list[uuid.UUID] | None = None,
) -> None:
    """シード済み装置にダミー画像を付与する（MinIO 未起動時はログのみ）。"""
    ids = device_ids if device_ids is not None else list(SEED_DEVICE_IDS)
    png = mini_png_bytes()
    try:
        content_type = validate_device_image_bytes(png)
    except ValueError as e:
        logger.warning("シード用 PNG が無効です: %s", e)
        return
    try:
        await asyncio.to_thread(ensure_device_images_bucket)
    except Exception as e:
        logger.warning("MinIO バケット確認に失敗しました（スキップ）: %s", e)
        return

    async with factory() as session:
        result = await session.execute(select(Device).where(Device.id.in_(ids)))
        devices = list(result.scalars().all())
        for device in devices:
            try:
                old_key = device.image_object_key
                key = await asyncio.to_thread(
                    put_device_image_object,
                    device_id=device.id,
                    body=png,
                    content_type=content_type,
                )
                await asyncio.to_thread(delete_device_image_object, object_key=old_key)
                device.image_object_key = key
                device.image_content_type = content_type
            except Exception as e:
                logger.warning("装置 %s の画像シードをスキップ: %s", device.id, e)
        await session.commit()
