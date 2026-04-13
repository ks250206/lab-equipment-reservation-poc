from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def init_db(bind: AsyncEngine | None = None) -> None:
    """メタデータに基づき不足テーブルを作成する。モデルは import 順に依存しない。"""
    from .models import Device, Reservation, User  # noqa: F401

    target = bind or engine
    async with target.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in (
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS image_object_key VARCHAR(512)",
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS image_content_type VARCHAR(64)",
        ):
            await conn.execute(text(stmt))
