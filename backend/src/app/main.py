import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db
from .routers import devices_router, reservations_router, users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from .storage.s3_device_images import ensure_device_images_bucket

        await asyncio.to_thread(ensure_device_images_bucket)
    except Exception as e:
        logger.warning("MinIO バケット初期化をスキップ: %s", e)
    yield


app = FastAPI(
    title="研究室装置予約システム",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users_router)
app.include_router(devices_router)
app.include_router(reservations_router)
