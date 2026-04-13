import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base
from app.models import Device, User
from app.services.users import (
    create_user,
    get_user,
    get_users,
    update_user,
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
            email="test@example.com",
            name="テストユーザー",
        )

        assert result.id is not None
        assert result.keycloak_id == "test-keycloak-id"
        assert result.email == "test@example.com"
        assert result.name == "テストユーザー"
        assert result.role == "user"
        assert result.created_at is not None


class TestGetUser:
    async def test_get_user_success(self, session: AsyncSession):
        created = await create_user(
            session,
            keycloak_id="test-keycloak-id",
            email="test@example.com",
        )
        result = await get_user(session, created.id)

        assert result is not None
        assert result.id == created.id
        assert result.email == "test@example.com"

    async def test_get_user_not_found(self, session: AsyncSession):
        fake_id = uuid.uuid4()
        result = await get_user(session, fake_id)

        assert result is None


class TestGetUsers:
    async def test_get_users_empty(self, session: AsyncSession):
        result = await get_users(session)

        assert len(result) == 0

    async def test_get_users_multiple(self, session: AsyncSession):
        await create_user(session, keycloak_id="user1", email="user1@test.com")
        await create_user(session, keycloak_id="user2", email="user2@test.com")

        result = await get_users(session)

        assert len(result) == 2


class TestUpdateUser:
    async def test_update_user_success(self, session: AsyncSession):
        user = await create_user(session, keycloak_id="test-id", email="test@test.com")

        from app.schemas import UserUpdate

        updated = await update_user(session, user, UserUpdate(name="更新名", role="admin"))

        assert updated.name == "更新名"
        assert updated.role == "admin"

    async def test_update_user_partial(self, session: AsyncSession):
        user = await create_user(
            session, keycloak_id="test-id", email="test@test.com", name="元の名前"
        )

        from app.schemas import UserUpdate

        updated = await update_user(session, user, UserUpdate(name="新名前"))

        assert updated.name == "新名前"
        assert updated.email == "test@test.com"


class TestReservationService:
    async def test_create_reservation_success(self, session: AsyncSession):
        device = Device(name="テスト装置")
        session.add(device)
        await session.commit()
        await session.refresh(device)

        user = User(keycloak_id="test-user", email="test@test.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation

        reservation = await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
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

        user = User(keycloak_id="test-user-overlap", email="overlap@test.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation

        await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
            ),
            user.id,
        )

        overlap = await check_time_overlap(
            session,
            device.id,
            datetime(2026, 4, 15, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 15, 13, 0, tzinfo=timezone.utc),
        )

        assert overlap is True

        no_overlap = await check_time_overlap(
            session,
            device.id,
            datetime(2026, 4, 15, 14, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 15, 16, 0, tzinfo=timezone.utc),
        )

        assert no_overlap is False

    async def test_get_reservations_by_user(self, session: AsyncSession):
        device = Device(name="テスト装置")
        session.add(device)
        await session.commit()
        await session.refresh(device)

        user = User(keycloak_id="test-user", email="test@test.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.schemas import ReservationCreate
        from app.services.reservations import create_reservation, get_reservations_by_user

        await create_reservation(
            session,
            ReservationCreate(
                device_id=device.id,
                start_time=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
            ),
            user.id,
        )

        result = await get_reservations_by_user(session, user.id)

        assert len(result) == 1
        assert result[0].user_id == user.id
