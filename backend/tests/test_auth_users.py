"""Keycloak ペイロードからのユーザー解決（DB 実体）。"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.auth as auth_mod
from app.auth import (
    get_or_create_user_from_payload,
    is_app_admin_from_payload,
    me_profile_fields_from_payload,
    realm_roles_from_payload,
)
from app.config import settings
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
    existing = User(keycloak_id="same-kc")
    session.add(existing)
    await session.commit()
    await session.refresh(existing)

    user = await get_or_create_user_from_payload(
        session,
        {"sub": "same-kc", "email": "ignored@test.com", "name": "無視"},
    )
    assert user.id == existing.id
    assert user.keycloak_id == "same-kc"


@pytest.mark.asyncio
async def test_get_or_create_inserts_without_email(session: AsyncSession):
    user = await get_or_create_user_from_payload(session, {"sub": "anon-kc-1"})
    assert user.keycloak_id == "anon-kc-1"

    result = await session.execute(select(User).where(User.keycloak_id == "anon-kc-1"))
    assert result.scalar_one().id == user.id


@pytest.mark.asyncio
async def test_get_or_create_rejects_missing_sub(session: AsyncSession):
    with pytest.raises(HTTPException) as exc:
        await get_or_create_user_from_payload(session, {"email": "x@test.com"})
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_or_create_inserts_with_invalid_email_claim(session: AsyncSession):
    user = await get_or_create_user_from_payload(
        session,
        {"sub": "kc-bad-email", "email": "not-an-email"},
    )
    assert user.keycloak_id == "kc-bad-email"


def test_me_profile_fields_coerce_invalid_email():
    email, _name = me_profile_fields_from_payload(
        {"email": "not-an-email"},
        "kc-bad-email",
    )
    assert email == "kc-bad-email@unknown.local"


def test_realm_roles_from_payload_parses_roles():
    assert realm_roles_from_payload({"realm_access": {"roles": ["a", "b"]}}) == {"a", "b"}
    assert realm_roles_from_payload({}) == set()
    assert realm_roles_from_payload({"realm_access": {}}) == set()


def test_is_app_admin_from_payload(monkeypatch):
    monkeypatch.setattr(
        auth_mod,
        "settings",
        SimpleNamespace(keycloak_app_admin_realm_role="app-admin"),
    )
    assert is_app_admin_from_payload({"realm_access": {"roles": ["app-admin"]}})
    assert not is_app_admin_from_payload({"realm_access": {"roles": ["user"]}})


@pytest.mark.asyncio
async def test_user_response_from_orm(session: AsyncSession):
    u = User(keycloak_id="kc-x")
    session.add(u)
    await session.commit()
    await session.refresh(u)
    body = UserResponse.model_validate(u)
    assert body.keycloak_id == "kc-x"
    assert body.id == u.id
