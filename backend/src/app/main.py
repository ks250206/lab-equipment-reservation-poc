from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db
from .routers import devices_router, reservations_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="室内装置予約システム",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users_router)
app.include_router(devices_router)
app.include_router(reservations_router)
