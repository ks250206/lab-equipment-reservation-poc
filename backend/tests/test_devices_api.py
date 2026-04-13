"""装置 API の結合テスト（認証は依存性オーバーライド）。"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_payload_utils import jwt_like_payload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_current_user, get_token_payload
from app.config import ReservationStatus, settings
from app.db import Base, get_session
from app.main import app
from app.models import Device, Reservation, User


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
        admin = User(keycloak_id="devices-admin")
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
        user = User(keycloak_id="devices-user")
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
    body = r.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 50}


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
    body = r.json()
    names = {row["name"] for row in body["items"]}
    assert names == {"A1"}
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_list_devices_pagination(devices_client):
    client, session = devices_client
    session.add_all([Device(name=f"D{i:03}", category="c") for i in range(25)])
    await session.commit()

    p1 = await client.get("/api/devices", params={"category": "c", "page": 1, "page_size": 20})
    assert p1.status_code == 200
    b1 = p1.json()
    assert b1["total"] == 25
    assert b1["page"] == 1
    assert b1["page_size"] == 20
    assert len(b1["items"]) == 20

    p2 = await client.get("/api/devices", params={"category": "c", "page": 2, "page_size": 20})
    assert p2.status_code == 200
    b2 = p2.json()
    assert len(b2["items"]) == 5


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


@pytest.mark.asyncio
async def test_list_devices_filter_by_reservation_user_and_window(devices_client):
    client, session = devices_client
    other = User(
        keycloak_id="resv-filter-user", name="山田テスト", email="yamada-filter@example.com"
    )
    session.add(other)
    await session.flush()

    d_match = Device(name="HasRes", category="c1", location="loc-a")
    d_other = Device(name="NoRes", category="c2", location="loc-b")
    session.add_all([d_match, d_other])
    await session.flush()

    t0 = datetime(2030, 6, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2030, 6, 1, 11, 0, tzinfo=UTC)
    session.add(
        Reservation(
            device_id=d_match.id,
            user_id=other.id,
            start_time=t0,
            end_time=t1,
            purpose="試験",
            status=ReservationStatus.CONFIRMED,
        )
    )
    await session.commit()

    match_id = str(d_match.id)
    other_id = str(d_other.id)

    r_user = await client.get("/api/devices", params={"reservation_user": "yamada-filter"})
    assert r_user.status_code == 200
    user_ids = {row["id"] for row in r_user.json()["items"]}
    assert match_id in user_ids
    assert other_id not in user_ids

    r_nomatch = await client.get(
        "/api/devices", params={"reservation_user": "存在しない名前_xyz_993311"}
    )
    assert r_nomatch.status_code == 200
    nomatch_ids = {row["id"] for row in r_nomatch.json()["items"]}
    assert match_id not in nomatch_ids

    r_win = await client.get(
        "/api/devices",
        params={
            "reservation_from": "2030-06-01T09:30:00Z",
            "reservation_to": "2030-06-01T10:30:00Z",
        },
    )
    assert r_win.status_code == 200
    win_ids = {row["id"] for row in r_win.json()["items"]}
    assert match_id in win_ids
    assert other_id not in win_ids

    r_win_miss = await client.get(
        "/api/devices",
        params={
            "reservation_from": "2030-06-02T00:00:00Z",
            "reservation_to": "2030-06-02T01:00:00Z",
        },
    )
    assert r_win_miss.status_code == 200
    miss_ids = {row["id"] for row in r_win_miss.json()["items"]}
    assert match_id not in miss_ids

    r_combo = await client.get(
        "/api/devices",
        params={
            "reservation_user": "yamada-filter",
            "reservation_from": "2030-06-01T00:00:00Z",
            "reservation_to": "2030-06-02T00:00:00Z",
        },
    )
    assert r_combo.status_code == 200
    combo_ids = {row["id"] for row in r_combo.json()["items"]}
    assert match_id in combo_ids
    assert other_id not in combo_ids
