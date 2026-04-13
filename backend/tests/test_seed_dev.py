from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, settings
from app.db import Base
from app.models import Device, Reservation, User
from app.seeding.dev_seed import (
    DEVICE_ROWS,
    RESERVATIONS_PER_DEVICE,
    build_reservation_seed_rows,
    offline_seed_user_rows,
    uid,
)
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


def test_settings_require_explicit_core_config_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_settings_accept_explicit_core_config_from_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ENVIRONMENT=production",
                "DATABASE_URL=postgresql+asyncpg://prod_user:prod_password@db:5432/equipment_reservation",
                "KEYCLOAK_URL=https://auth.example.test",
                "KEYCLOAK_REALM=laboratory",
                "KEYCLOAK_CLIENT_ID=equipment-reservation",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("ENVIRONMENT", raising=False)
    cfg = Settings(_env_file=env_file)

    assert cfg.is_production


@pytest.mark.asyncio
async def test_seed_dev_idempotent(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert not Settings().is_production

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    rows = offline_seed_user_rows()
    await run_seed(session_factory=factory, user_rows=rows)
    async with factory() as session:
        n1 = await session.scalar(select(func.count()).select_from(Device))
        u1 = await session.scalar(select(func.count()).select_from(User))
        r1 = await session.scalar(select(func.count()).select_from(Reservation))
    await run_seed(session_factory=factory, user_rows=rows)
    async with factory() as session:
        n2 = await session.scalar(select(func.count()).select_from(Device))
        u2 = await session.scalar(select(func.count()).select_from(User))
        r2 = await session.scalar(select(func.count()).select_from(Reservation))
    assert n1 == n2 == 33
    assert u1 == u2 == 8
    expected_res = len(DEVICE_ROWS) * RESERVATIONS_PER_DEVICE
    assert r1 == r2 == expected_res
    async with factory() as session:
        yamada = await session.get(User, uid("yamada"))
        assert yamada is not None
        assert yamada.email == "yamada.taro@example.local"
        assert yamada.name == "山田 太郎"


def test_build_reservation_seed_rows_two_month_window() -> None:
    at = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    rows = build_reservation_seed_rows(at=at)
    assert len(rows) == len(DEVICE_ROWS) * RESERVATIONS_PER_DEVICE
    win_start = datetime(2026, 3, 1, tzinfo=UTC)
    win_end = datetime(2026, 5, 1, tzinfo=UTC)
    for row in rows:
        st = row["start_time"]
        et = row["end_time"]
        assert win_start <= st < win_end
        assert st < et <= win_end
