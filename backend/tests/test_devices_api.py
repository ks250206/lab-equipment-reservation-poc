"""装置 API の結合テスト（認証は依存性オーバーライド）。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_payload_utils import jwt_like_payload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_current_user, get_token_payload
from app.config import UserRole, settings
from app.db import Base, get_session
from app.main import app
from app.models import Device, User


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
async def devices_client(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        admin = User(
            keycloak_id="devices-admin",
            email="admin-devices@test.com",
            role=UserRole.ADMIN,
        )
        shared.add(admin)
        await shared.flush()
        await shared.refresh(admin)

        async def override_get_session():
            yield shared

        async def override_get_current_user():
            row = await shared.get(User, admin.id)
            assert row is not None
            return row

        async def override_get_token_payload():
            return jwt_like_payload(
                sub=admin.keycloak_id,
                realm_roles=["app-admin"],
            )

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_token_payload] = override_get_token_payload

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, shared

    app.dependency_overrides.clear()


@pytest.fixture
async def devices_anon_client(engine):
    """管理者以外（装置の書き込みは 403）。"""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        user = User(keycloak_id="devices-user", email="user-devices@test.com", role=UserRole.USER)
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
            )

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_token_payload] = override_get_token_payload

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, shared

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_devices_empty(devices_client):
    client, _ = devices_client
    r = await client.get("/api/devices")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_devices_with_filters(devices_client):
    client, session = devices_client
    session.add_all(
        [
            Device(name="A1", category="cat1", location="lab1"),
            Device(name="B2", category="cat2", location="lab2"),
        ]
    )
    await session.commit()

    r = await client.get("/api/devices", params={"category": "cat1"})
    assert r.status_code == 200
    names = {row["name"] for row in r.json()}
    assert names == {"A1"}


@pytest.mark.asyncio
async def test_get_device_facets(devices_client):
    client, session = devices_client
    session.add(Device(name="F1", category="x", location="y"))
    await session.commit()

    r = await client.get("/api/devices/facets")
    assert r.status_code == 200
    body = r.json()
    assert "category" in body and "location" in body and "status" in body


@pytest.mark.asyncio
async def test_get_device_by_id(devices_client):
    client, session = devices_client
    d = Device(name="単体")
    session.add(d)
    await session.commit()
    await session.refresh(d)

    ok = await client.get(f"/api/devices/{d.id}")
    assert ok.status_code == 200
    assert ok.json()["name"] == "単体"

    bad = await client.get("/api/devices/not-uuid")
    assert bad.status_code == 400

    missing = await client.get(f"/api/devices/{uuid.uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_create_update_delete_device(devices_client):
    client, _ = devices_client
    created = await client.post(
        "/api/devices",
        json={
            "name": "新規装置",
            "description": "desc",
            "location": "L1",
            "category": "C1",
        },
    )
    assert created.status_code == 200
    did = created.json()["id"]

    updated = await client.put(
        f"/api/devices/{did}",
        json={"name": "改名"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "改名"

    deleted = await client.delete(f"/api/devices/{did}")
    assert deleted.status_code == 204

    gone = await client.get(f"/api/devices/{did}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_update_delete_device_invalid_id_400(devices_client):
    client, _ = devices_client
    assert (await client.put("/api/devices/not-uuid", json={"name": "x"})).status_code == 400
    assert (await client.delete("/api/devices/not-uuid")).status_code == 400


@pytest.mark.asyncio
async def test_update_delete_device_not_found_404(devices_client):
    client, _ = devices_client
    rid = str(uuid.uuid4())
    assert (await client.put(f"/api/devices/{rid}", json={"name": "x"})).status_code == 404
    assert (await client.delete(f"/api/devices/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_device_write_requires_admin(devices_anon_client):
    client, _ = devices_anon_client
    r = await client.post(
        "/api/devices",
        json={"name": "NG", "description": None, "location": None, "category": None},
    )
    assert r.status_code == 403
