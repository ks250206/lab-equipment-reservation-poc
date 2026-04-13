import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base
from app.models import Device, User
from app.services.users import (
    create_user,
    get_user,
    get_users,
)


@pytest.fixture
async def engine():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestCreateUser:
    async def test_create_user_success(self, session: AsyncSession):
        result = await create_user(
            session,
            keycloak_id="test-keycloak-id",
        )

        assert result.id is not None
        assert result.keycloak_id == "test-keycloak-id"
        assert result.created_at is not None


class TestGetUser:
    async def test_get_user_success(self, session: AsyncSession):
        created = await create_user(
            session,
            keycloak_id="test-keycloak-id",
        )
        result = await get_user(session, created.id)

        assert result is not None
        assert result.id == created.id
        assert result.keycloak_id == "test-keycloak-id"

    async def test_get_user_not_found(self, session: AsyncSession):
        fake_id = uuid.uuid4()
        result = await get_user(session, fake_id)

        assert result is None


class TestGetUsers:
    async def test_get_users_empty(self, session: AsyncSession):
        result = await get_users(session)

        assert len(result) == 0

    async def test_get_users_multiple(self, session: AsyncSession):
        await create_user(session, keycloak_id="user1")
        await create_user(session, keycloak_id="user2")

        result = await get_users(session)

        assert len(result) == 2


class TestReservationService:
    async def test_create_reservation_success(self, session: AsyncSession):
        device = Device(name="テスト装置")
        session.add(device)
        await session.commit()
        await session.refresh(device)

        user = User(keycloak_id="test-user")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation

        reservation = await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
                purpose="テスト目的",
            ),
            user.id,
        )

        assert reservation.id is not None
        assert reservation.device_id == device.id
        assert reservation.user_id == user.id
        assert reservation.status == "confirmed"

    async def test_create_reservation_overlap_check(self, session: AsyncSession):
        from app.services.reservations import check_time_overlap

        device = Device(name="テスト装置")
        session.add(device)
        await session.commit()
        await session.refresh(device)

        user = User(keycloak_id="test-user-overlap")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation

        await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
            ),
            user.id,
        )

        overlap = await check_time_overlap(
            session,
            device.id,
            datetime(2026, 4, 15, 11, 0, tzinfo=UTC),
            datetime(2026, 4, 15, 13, 0, tzinfo=UTC),
        )

        assert overlap is True

        no_overlap = await check_time_overlap(
            session,
            device.id,
            datetime(2026, 4, 15, 14, 0, tzinfo=UTC),
            datetime(2026, 4, 15, 16, 0, tzinfo=UTC),
        )

        assert no_overlap is False

    async def test_get_reservations_by_user(self, session: AsyncSession):
        device = Device(name="テスト装置")
        session.add(device)
        await session.commit()
        await session.refresh(device)

        user = User(keycloak_id="test-user")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation, get_reservations_by_user

        await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
            ),
            user.id,
        )

        result = await get_reservations_by_user(session, user.id)

        assert len(result) == 1
        assert result[0].user_id == user.id

    async def test_get_reservation_by_id(self, session: AsyncSession):
        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation, get_reservation

        device = Device(name="get1")
        session.add(device)
        user = User(keycloak_id="get-r")
        session.add_all([device, user])
        await session.commit()
        await session.refresh(device)
        await session.refresh(user)

        created = await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
            ),
            user.id,
        )

        found = await get_reservation(session, created.id)
        assert found is not None
        assert found.id == created.id

        missing = await get_reservation(session, uuid.uuid4())
        assert missing is None

    async def test_get_reservations_by_device(self, session: AsyncSession):
        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation, get_reservations_by_device

        device = Device(name="dev-list")
        user = User(keycloak_id="dev-list-u")
        session.add_all([device, user])
        await session.commit()
        await session.refresh(device)
        await session.refresh(user)

        await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 5, 2, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 2, 11, 0, tzinfo=UTC),
            ),
            user.id,
        )

        rows = await get_reservations_by_device(session, device.id)
        assert len(rows) == 1
        assert rows[0].device_id == device.id

    async def test_update_and_delete_reservation_service(self, session: AsyncSession):
        from app.schemas import ReservationCreate, ReservationUpdate
        from app.services.reservations import (
            create_reservation,
            delete_reservation,
            get_reservation,
            update_reservation,
        )

        device = Device(name="upd-del")
        user = User(keycloak_id="upd-del-u")
        session.add_all([device, user])
        await session.commit()
        await session.refresh(device)
        await session.refresh(user)

        res = await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 5, 3, 10, 0, tzinfo=UTC),
                end_time=datetime(2026, 5, 3, 11, 0, tzinfo=UTC),
                purpose="元",
            ),
            user.id,
        )

        updated = await update_reservation(session, res, ReservationUpdate(purpose="更新後"))
        assert updated.purpose == "更新後"

        re_times = await update_reservation(
            session, updated, ReservationUpdate(start_time=datetime(2026, 5, 3, 10, 15))
        )
        assert re_times.start_time.tzinfo is not None

        await delete_reservation(session, re_times)
        assert await get_reservation(session, res.id) is None

    async def test_delete_completed_reservation_raises(self, session: AsyncSession):
        from app.config import ReservationStatus
        from app.models import Reservation
        from app.services.reservations import delete_reservation, get_reservation

        device = Device(name="svc-completed")
        user = User(keycloak_id="svc-completed-u")
        session.add_all([device, user])
        await session.commit()
        await session.refresh(device)
        await session.refresh(user)

        row = Reservation(
            device_id=device.id,
            user_id=user.id,
            start_time=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 5, 20, 11, 0, tzinfo=UTC),
            status=ReservationStatus.COMPLETED,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)

        with pytest.raises(ValueError, match="Completed"):
            await delete_reservation(session, row)

        assert await get_reservation(session, row.id) is not None
