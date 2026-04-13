"""ユーザー API の結合テスト（認証は依存性オーバーライド）。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_payload_utils import jwt_like_payload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_current_user, get_token_payload
from app.config import settings
from app.db import Base, get_session
from app.main import app
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
async def users_admin_client(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        admin = User(keycloak_id="users-admin-kc")
        other = User(keycloak_id="users-other-kc")
        shared.add_all([admin, other])
        await shared.flush()
        await shared.refresh(admin)
        await shared.refresh(other)

        async def override_get_session():
            yield shared

        async def override_get_current_user():
            row = await shared.get(User, admin.id)
            assert row is not None
            return row

        async def override_get_token_payload():
            return jwt_like_payload(
                sub=admin.keycloak_id,
                realm_roles=["app-admin", "offline_access"],
                email="users-admin@test.com",
                name="管理者",
            )

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_token_payload] = override_get_token_payload

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, shared, admin, other

    app.dependency_overrides.clear()


@pytest.fixture
async def users_regular_client(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        user = User(keycloak_id="users-regular-kc")
        shared.add(user)
        await shared.flush()
        await shared.refresh(user)

        async def override_get_session():
            yield shared

        async def override_get_current_user():
            row = await shared.get(User, user.id)
            assert row is not None
            return row

        async def override_get_token_payload():
            return jwt_like_payload(
                sub=user.keycloak_id,
                realm_roles=["default-roles-master"],
                email="regular@test.com",
            )

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_token_payload] = override_get_token_payload

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, shared, user

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_me(users_admin_client):
    client, _session, admin, _other = users_admin_client
    r = await client.get("/api/users/me")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(admin.id)
    assert body["email"] == "users-admin@test.com"
    assert body["name"] == "管理者"
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_list_users_admin(users_admin_client):
    client, _session, _admin, _other = users_admin_client
    r = await client.get("/api/users")
    assert r.status_code == 200
    rows = r.json()
    kc_ids = {row["keycloak_id"] for row in rows}
    assert "users-admin-kc" in kc_ids
    assert "users-other-kc" in kc_ids
    for row in rows:
        assert "email" not in row
        assert "name" not in row


@pytest.mark.asyncio
async def test_get_user_by_id(users_admin_client):
    client, _session, _admin, other = users_admin_client

    ok = await client.get(f"/api/users/{other.id}")
    assert ok.status_code == 200
    assert ok.json()["keycloak_id"] == "users-other-kc"

    bad = await client.get("/api/users/not-uuid")
    assert bad.status_code == 400

    missing = await client.get(f"/api/users/{uuid.uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_users_forbidden_for_non_admin(users_regular_client):
    client, _session, _user = users_regular_client
    r = await client.get("/api/users")
    assert r.status_code == 403
