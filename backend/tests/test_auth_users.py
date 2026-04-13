"""Keycloak ペイロードからのユーザー解決（DB 実体）。"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.auth as auth_mod
from app.auth import get_or_create_user_from_payload
from app.config import UserRole, settings
from app.db import Base
from app.models import User
from app.schemas import UserResponse


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


@pytest.mark.asyncio
async def test_get_or_create_coerces_invalid_email(session: AsyncSession):
    user = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-bad-email", "email": "not-an-email"},
    )
    assert user.email == "kc-bad-email@unknown.local"


@pytest.mark.asyncio
async def test_get_or_create_bootstrap_admin_by_preferred_username(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        auth_mod,
        "settings",
        SimpleNamespace(
            keycloak_bootstrap_admin_usernames="alice,bob",
            is_development=False,
        ),
    )
    admin_user = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-a1", "preferred_username": "alice", "email": "alice@example.com"},
    )
    assert admin_user.role == UserRole.ADMIN

    plain = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-u2", "preferred_username": "charlie", "email": "c@example.com"},
    )
    assert plain.role == UserRole.USER


@pytest.mark.asyncio
async def test_get_or_create_dev_grants_admin_for_keycloak_admin_username(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """development かつ env 未指定でも preferred_username=admin をアプリ admin にする。"""
    monkeypatch.setattr(
        auth_mod,
        "settings",
        SimpleNamespace(keycloak_bootstrap_admin_usernames="", is_development=True),
    )
    u = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-dev-admin", "preferred_username": "admin", "email": "a@example.com"},
    )
    assert u.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_get_or_create_production_no_default_admin_without_env(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        auth_mod,
        "settings",
        SimpleNamespace(keycloak_bootstrap_admin_usernames="", is_development=False),
    )
    u = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-prod", "preferred_username": "admin", "email": "a@example.com"},
    )
    assert u.role == UserRole.USER


@pytest.mark.asyncio
async def test_user_response_accepts_non_rfc_email_from_orm(session: AsyncSession):
    u = User(keycloak_id="kc-x", email="admin", role=UserRole.USER)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    body = UserResponse.model_validate(u)
    assert body.email == "admin"
