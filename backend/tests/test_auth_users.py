"""Keycloak ペイロードからのユーザー解決（DB 実体）。"""

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_or_create_user_from_payload
from app.config import settings
from app.db import Base
from app.models import User


@pytest.fixture
async def engine():
    eng = create_async_engine(settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(session: AsyncSession):
    existing = User(keycloak_id="same-kc", email="keep@test.com", name="既存")
    session.add(existing)
    await session.commit()
    await session.refresh(existing)

    user = await get_or_create_user_from_payload(
        session,
        {"sub": "same-kc", "email": "ignored@test.com", "name": "無視"},
    )
    assert user.id == existing.id
    assert user.email == "keep@test.com"


@pytest.mark.asyncio
async def test_get_or_create_inserts_without_email(session: AsyncSession):
    user = await get_or_create_user_from_payload(session, {"sub": "anon-kc-1"})
    assert user.keycloak_id == "anon-kc-1"
    assert user.email == "anon-kc-1@unknown.local"

    result = await session.execute(select(User).where(User.keycloak_id == "anon-kc-1"))
    assert result.scalar_one().id == user.id


@pytest.mark.asyncio
async def test_get_or_create_rejects_missing_sub(session: AsyncSession):
    with pytest.raises(HTTPException) as exc:
        await get_or_create_user_from_payload(session, {"email": "x@test.com"})
    assert exc.value.status_code == 401
