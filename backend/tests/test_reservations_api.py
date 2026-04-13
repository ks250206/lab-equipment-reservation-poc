"""予約 API の結合テスト（認証は依存性オーバーライド）。"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
async def reservation_client(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as shared:
        owner = User(keycloak_id="reservation-api-owner", email="owner@test.com")
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
async def test_post_reservation_success(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="API 用装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    response = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T10:00:00Z",
            "end_time": "2026-04-15T12:00:00Z",
            "purpose": "結合試験",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == str(device.id)
    assert body["user_id"] == str(owner.id)
    assert body["purpose"] == "結合試験"


@pytest.mark.asyncio
async def test_post_reservation_overlap_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="重複テスト装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    first = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T10:00:00Z",
            "end_time": "2026-04-15T12:00:00Z",
        },
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T11:00:00Z",
            "end_time": "2026-04-15T13:00:00Z",
        },
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_put_reservation_overlap_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="更新重複装置")
    session.add(device)
    other = User(keycloak_id="other-user", email="other@test.com")
    session.add(other)
    await session.commit()
    await session.refresh(device)
    await session.refresh(other)

    mine = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T10:00:00Z",
            "end_time": "2026-04-15T12:00:00Z",
        },
    )
    assert mine.status_code == 200
    my_id = mine.json()["id"]

    session.add(
        Reservation(
            device_id=device.id,
            user_id=other.id,
            start_time=datetime(2026, 4, 15, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 4, 15, 16, 0, tzinfo=timezone.utc),
            status=ReservationStatus.CONFIRMED,
        )
    )
    await session.commit()

    conflict = await client.put(
        f"/api/reservations/{my_id}",
        json={"end_time": "2026-04-15T15:00:00Z"},
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_put_reservation_cancelled_skips_overlap(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="キャンセル装置")
    session.add(device)
    other = User(keycloak_id="other-user-2", email="other2@test.com")
    session.add(other)
    await session.commit()
    await session.refresh(device)
    await session.refresh(other)

    mine = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T10:00:00Z",
            "end_time": "2026-04-15T12:00:00Z",
        },
    )
    assert mine.status_code == 200
    my_id = mine.json()["id"]

    session.add(
        Reservation(
            device_id=device.id,
            user_id=other.id,
            start_time=datetime(2026, 4, 15, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 4, 15, 13, 0, tzinfo=timezone.utc),
            status=ReservationStatus.CONFIRMED,
        )
    )
    await session.commit()

    cancel = await client.put(
        f"/api/reservations/{my_id}",
        json={"status": "cancelled"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_list_reservations_only_own(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="一覧装置")
    session.add(device)
    other = User(keycloak_id="lister-other", email="lister@test.com")
    session.add(other)
    await session.flush()
    await session.refresh(device)
    await session.refresh(other)

    session.add(
        Reservation(
            device_id=device.id,
            user_id=other.id,
            start_time=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
            status=ReservationStatus.CONFIRMED,
        )
    )
    await session.commit()

    await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-20T10:00:00Z",
            "end_time": "2026-04-20T11:00:00Z",
        },
    )

    listed = await client.get("/api/reservations")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["user_id"] == str(owner.id)


@pytest.mark.asyncio
async def test_delete_reservation(reservation_client):
    client, session, _owner = reservation_client
    device = Device(name="削除装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    created = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-21T10:00:00Z",
            "end_time": "2026-04-21T11:00:00Z",
        },
    )
    rid = created.json()["id"]

    deleted = await client.delete(f"/api/reservations/{rid}")
    assert deleted.status_code == 204

    result = await session.execute(select(Reservation).where(Reservation.id == uuid.UUID(rid)))
    assert result.scalar_one_or_none() is None
