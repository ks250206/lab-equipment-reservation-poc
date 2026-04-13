"""GET /api/devices/{id}/reservations の結合テスト。"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_current_user
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
async def device_reservations_client(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        owner = User(keycloak_id="device-reservations-viewer")
        shared.add(owner)
        await shared.flush()
        await shared.refresh(owner)

        async def override_get_session():
            yield shared

        async def override_get_current_user():
            row = await shared.get(User, owner.id)
            assert row is not None
            return row

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, shared, owner

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_device_reservations_filters_by_window(device_reservations_client):
    client, session, owner = device_reservations_client
    device = Device(name="窓テスト装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    session.add_all(
        [
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
                purpose="窓内A",
            ),
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
                end_time=datetime(2026, 6, 1, 1, 0, tzinfo=UTC),
                purpose="窓外",
            ),
        ]
    )
    await session.commit()

    r = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-05-01T00:00:00Z",
            "to": "2026-05-31T23:59:59Z",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["purpose"] == "窓内A"


@pytest.mark.asyncio
async def test_list_device_reservations_excludes_cancelled_by_default(device_reservations_client):
    client, session, owner = device_reservations_client
    device = Device(name="キャンセル装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    session.add_all(
        [
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=datetime(2026, 5, 10, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 10, 11, 0, tzinfo=UTC),
                purpose="有効",
            ),
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
                purpose="取消",
                status=ReservationStatus.CANCELLED,
            ),
        ]
    )
    await session.commit()

    r = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-05-10T00:00:00Z",
            "to": "2026-05-11T00:00:00Z",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1

    r2 = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-05-10T00:00:00Z",
            "to": "2026-05-11T00:00:00Z",
            "include_cancelled": "true",
        },
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["total"] == 2
    assert len(b2["items"]) == 2


@pytest.mark.asyncio
async def test_list_device_reservations_pagination(device_reservations_client):
    client, session, owner = device_reservations_client
    device = Device(name="ページ装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    base = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    for h in range(25):
        start = base + timedelta(hours=h)
        session.add(
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=start,
                end_time=start + timedelta(hours=1),
                purpose=f"R{h}",
            )
        )
    await session.commit()

    p1 = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-07-01T00:00:00Z",
            "to": "2026-07-03T00:00:00Z",
            "page": 1,
            "page_size": 20,
        },
    )
    assert p1.status_code == 200
    j1 = p1.json()
    assert j1["total"] == 25
    assert len(j1["items"]) == 20
    assert j1["items"][0]["purpose"] == "R0"

    p2 = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-07-01T00:00:00Z",
            "to": "2026-07-03T00:00:00Z",
            "page": 2,
            "page_size": 20,
        },
    )
    assert p2.status_code == 200
    j2 = p2.json()
    assert len(j2["items"]) == 5
    assert j2["items"][0]["purpose"] == "R20"


@pytest.mark.asyncio
async def test_list_device_reservations_from_without_to_returns_400(device_reservations_client):
    client, session, owner = device_reservations_client
    device = Device(name="片方だけ")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    r = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={"from": "2026-05-01T00:00:00Z"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_device_reservations_invalid_range_returns_400(device_reservations_client):
    client, session, owner = device_reservations_client
    device = Device(name="逆転窓")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    r = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            "from": "2026-06-01T00:00:00Z",
            "to": "2026-05-01T00:00:00Z",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_device_reservations_unknown_device_returns_404(device_reservations_client):
    client, _, _ = device_reservations_client
    missing = uuid.uuid4()
    r = await client.get(
        f"/api/devices/{missing}/reservations",
        params={
            "from": "2026-05-01T00:00:00Z",
            "to": "2026-06-01T00:00:00Z",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_device_reservations_mine_only_and_status_filter(device_reservations_client):
    client, session, owner = device_reservations_client
    other = User(keycloak_id="other-resv-user")
    session.add(other)
    await session.flush()

    device = Device(name="絞り込み装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    t0 = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 7, 1, 11, 0, tzinfo=UTC)
    t3 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    session.add_all(
        [
            Reservation(
                device_id=device.id,
                user_id=owner.id,
                start_time=t0,
                end_time=t1,
                purpose="自分",
            ),
            Reservation(
                device_id=device.id,
                user_id=other.id,
                start_time=t2,
                end_time=t3,
                purpose="他人",
            ),
        ]
    )
    await session.commit()

    base_params = {
        "from": "2026-07-01T00:00:00Z",
        "to": "2026-07-02T00:00:00Z",
    }
    r_all = await client.get(f"/api/devices/{device.id}/reservations", params=base_params)
    assert r_all.status_code == 200
    assert r_all.json()["total"] == 2

    r_mine = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={**base_params, "mine_only": "true"},
    )
    assert r_mine.status_code == 200
    assert r_mine.json()["total"] == 1
    assert r_mine.json()["items"][0]["purpose"] == "自分"

    r_cancel = await client.get(
        f"/api/devices/{device.id}/reservations",
        params={
            **base_params,
            "reservation_status": "cancelled",
        },
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["total"] == 0
