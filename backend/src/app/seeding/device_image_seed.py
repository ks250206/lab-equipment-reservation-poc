"""開発シード: 各装置に識別しやすいダミー PNG を MinIO に投入する。"""

from __future__ import annotations

import asyncio
import colorsys
import logging
import uuid
from io import BytesIO

from PIL import Image, ImageDraw
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


def build_seed_png_bytes_for_device(device_id: uuid.UUID) -> bytes:
    """装置 ID ごとに色・図形が変わる小さな PNG（シードの目視確認用）。"""
    raw = int.from_bytes(device_id.bytes, "big")
    side = 56 + (raw % 4) * 8

    hue_a = (raw % 1000) / 1000.0
    hue_b = ((raw >> 20) % 1000) / 1000.0
    sat_a = 0.42 + (raw >> 8 & 0xFF) / 850.0
    sat_b = 0.38 + (raw >> 16 & 0xFF) / 900.0
    r1, g1, b1 = colorsys.hsv_to_rgb(hue_a, min(sat_a, 0.85), 0.92)
    r2, g2, b2 = colorsys.hsv_to_rgb(
        (hue_a * 0.6 + hue_b * 0.4 + 0.07) % 1.0, min(sat_b, 0.8), 0.78
    )
    base = (int(r1 * 255), int(g1 * 255), int(b1 * 255))
    accent = (int(r2 * 255), int(g2 * 255), int(b2 * 255))

    img = Image.new("RGB", (side, side), base)
    draw = ImageDraw.Draw(img)
    pattern = raw % 5
    m = side // 6
    if pattern == 0:
        draw.rectangle([0, 0, side // 2, side], fill=accent)
    elif pattern == 1:
        draw.rectangle([0, 0, side, side // 2], fill=accent)
    elif pattern == 2:
        draw.ellipse([m, m, side - m, side - m], fill=accent)
    elif pattern == 3:
        draw.rectangle([0, 0, side - m, side - m], outline=accent, width=max(2, side // 16))
    else:
        draw.polygon([(0, side), (side, side), (side // 2, m)], fill=accent)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def seed_device_images_after_devices(
    factory: async_sessionmaker[AsyncSession],
    *,
    device_ids: list[uuid.UUID] | None = None,
) -> None:
    """シード済み装置にダミー画像を付与する（MinIO 未起動時はログのみ）。"""
    ids = device_ids if device_ids is not None else list(SEED_DEVICE_IDS)
    try:
        await asyncio.to_thread(ensure_device_images_bucket)
    except Exception as e:
        logger.warning("MinIO バケット確認に失敗しました（スキップ）: %s", e)
        return

    async with factory() as session:
        result = await session.execute(select(Device).where(Device.id.in_(ids)))
        devices = list(result.scalars().all())
        for device in devices:
            png = build_seed_png_bytes_for_device(device.id)
            try:
                content_type = validate_device_image_bytes(png)
            except ValueError as e:
                logger.warning("装置 %s のシード PNG が無効です: %s", device.id, e)
                continue
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
