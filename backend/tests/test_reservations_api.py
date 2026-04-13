"""予約 API の結合テスト（認証は依存性オーバーライド）。"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.config import ReservationStatus, settings
from app.db import Base, get_session
from app.main import app
from app.models import Device, Reservation, User, UserFavoriteDevice


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
        owner = User(keycloak_id="reservation-api-owner")
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
    other = User(keycloak_id="other-user")
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
            start_time=datetime(2026, 4, 15, 14, 0, tzinfo=UTC),
            end_time=datetime(2026, 4, 15, 16, 0, tzinfo=UTC),
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
    other = User(keycloak_id="other-user-2")
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
            start_time=datetime(2026, 4, 15, 11, 0, tzinfo=UTC),
            end_time=datetime(2026, 4, 15, 13, 0, tzinfo=UTC),
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
    other = User(keycloak_id="lister-other")
    session.add(other)
    await session.flush()
    await session.refresh(device)
    await session.refresh(other)

    session.add(
        Reservation(
            device_id=device.id,
            user_id=other.id,
            start_time=datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 4, 20, 10, 0, tzinfo=UTC),
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
    body = listed.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["user_id"] == str(owner.id)


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


@pytest.mark.asyncio
async def test_delete_completed_reservation_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="完了済み削除不可")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    row = Reservation(
        device_id=device.id,
        user_id=owner.id,
        start_time=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 1, 11, 0, tzinfo=UTC),
        status=ReservationStatus.COMPLETED,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    r = await client.delete(f"/api/reservations/{row.id}")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_put_completed_reservation_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="完了済み更新不可")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    row = Reservation(
        device_id=device.id,
        user_id=owner.id,
        start_time=datetime(2026, 8, 2, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 8, 2, 11, 0, tzinfo=UTC),
        status=ReservationStatus.COMPLETED,
        purpose="確定済み",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    r = await client.put(f"/api/reservations/{row.id}", json={"purpose": "書き換え"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_post_reservation_unknown_device_404(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.post(
        "/api/reservations",
        json={
            "device_id": str(uuid.uuid4()),
            "start_time": "2026-04-15T10:00:00Z",
            "end_time": "2026-04-15T12:00:00Z",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_post_reservation_invalid_time_range_400(reservation_client):
    client, session, _owner = reservation_client
    device = Device(name="時間不正")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    r = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-04-15T12:00:00Z",
            "end_time": "2026-04-15T10:00:00Z",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_put_reservation_invalid_id_400(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.put(
        "/api/reservations/not-uuid",
        json={"purpose": "x"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_reservation_invalid_id_400(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.delete("/api/reservations/not-uuid")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_reservation_not_found_404(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.delete(f"/api/reservations/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_reservations_filter_by_device(reservation_client):
    client, session, _owner = reservation_client
    d1 = Device(name="D1")
    d2 = Device(name="D2")
    session.add_all([d1, d2])
    await session.commit()
    await session.refresh(d1)
    await session.refresh(d2)

    await client.post(
        "/api/reservations",
        json={
            "device_id": str(d1.id),
            "start_time": "2026-04-20T10:00:00Z",
            "end_time": "2026-04-20T11:00:00Z",
        },
    )
    await client.post(
        "/api/reservations",
        json={
            "device_id": str(d2.id),
            "start_time": "2026-04-21T10:00:00Z",
            "end_time": "2026-04-21T11:00:00Z",
        },
    )

    r = await client.get("/api/reservations", params={"device_id": str(d1.id)})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["device_id"] == str(d1.id)


@pytest.mark.asyncio
async def test_list_reservations_from_to_window(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="窓装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-05-10T12:00:00Z",
            "end_time": "2026-05-10T13:00:00Z",
        },
    )
    await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-06-01T12:00:00Z",
            "end_time": "2026-06-01T13:00:00Z",
        },
    )

    r = await client.get(
        "/api/reservations",
        params={
            "from": "2026-05-01T00:00:00Z",
            "to": "2026-05-31T23:59:59Z",
        },
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_reservations_from_without_to_400(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.get("/api/reservations", params={"from": "2026-05-01T00:00:00Z"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_reservations_invalid_status_422(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.get("/api/reservations", params={"reservation_status": "not-a-status"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_reservations_unknown_device_404(reservation_client):
    client, _session, _owner = reservation_client
    r = await client.get("/api/reservations", params={"device_id": str(uuid.uuid4())})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_post_complete_usage_success(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="完了報告装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    created = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-09-01T10:00:00Z",
            "end_time": "2026-09-01T11:00:00Z",
        },
    )
    assert created.status_code == 200
    rid = created.json()["id"]

    done = await client.post(f"/api/reservations/{rid}/complete-usage")
    assert done.status_code == 200
    assert done.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_post_complete_usage_not_confirmed_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="完了報告409装置")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    row = Reservation(
        device_id=device.id,
        user_id=owner.id,
        start_time=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 2, 11, 0, tzinfo=UTC),
        status=ReservationStatus.CANCELLED,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    r = await client.post(f"/api/reservations/{row.id}/complete-usage")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_put_reservation_status_completed_returns_409(reservation_client):
    client, session, owner = reservation_client
    device = Device(name="PUT完了禁止")
    session.add(device)
    await session.commit()
    await session.refresh(device)

    created = await client.post(
        "/api/reservations",
        json={
            "device_id": str(device.id),
            "start_time": "2026-09-03T10:00:00Z",
            "end_time": "2026-09-03T11:00:00Z",
        },
    )
    assert created.status_code == 200
    rid = created.json()["id"]

    r = await client.put(f"/api/reservations/{rid}", json={"status": "completed"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_reservations_favorites_only_filters(reservation_client):
    client, session, owner = reservation_client
    fav_dev = Device(name="お気に入り装置")
    other_dev = Device(name="その他装置")
    session.add_all([fav_dev, other_dev])
    await session.commit()
    await session.refresh(fav_dev)
    await session.refresh(other_dev)

    session.add(UserFavoriteDevice(user_id=owner.id, device_id=fav_dev.id))
    await session.commit()

    await client.post(
        "/api/reservations",
        json={
            "device_id": str(fav_dev.id),
            "start_time": "2026-09-10T10:00:00Z",
            "end_time": "2026-09-10T11:00:00Z",
        },
    )
    await client.post(
        "/api/reservations",
        json={
            "device_id": str(other_dev.id),
            "start_time": "2026-09-11T10:00:00Z",
            "end_time": "2026-09-11T11:00:00Z",
        },
    )

    all_rows = await client.get("/api/reservations")
    assert all_rows.status_code == 200
    assert all_rows.json()["total"] == 2

    fav_only = await client.get("/api/reservations", params={"favorites_only": "true"})
    assert fav_only.status_code == 200
    body = fav_only.json()
    assert body["total"] == 1
    assert body["items"][0]["device_id"] == str(fav_dev.id)
