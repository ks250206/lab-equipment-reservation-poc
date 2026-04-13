import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, settings
from app.db import Base
from app.models import Device, User
from app.seeding.runner import ensure_development_for_seed, run_seed


@pytest.fixture
async def engine():
    eng = create_async_engine(settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


def test_settings_invalid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    with pytest.raises(ValidationError):
        Settings()


def test_seed_guard_blocks_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="development"):
        ensure_development_for_seed()


@pytest.mark.asyncio
async def test_seed_dev_idempotent(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert not Settings().is_production

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await run_seed(session_factory=factory)
    async with factory() as session:
        n1 = await session.scalar(select(func.count()).select_from(Device))
        u1 = await session.scalar(select(func.count()).select_from(User))
    await run_seed(session_factory=factory)
    async with factory() as session:
        n2 = await session.scalar(select(func.count()).select_from(Device))
        u2 = await session.scalar(select(func.count()).select_from(User))
    assert n1 == n2 == 33
    assert u1 == u2 == 8
