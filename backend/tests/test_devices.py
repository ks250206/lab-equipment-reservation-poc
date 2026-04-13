import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base
from app.schemas import DeviceCreate, DeviceUpdate
from app.services.devices import (
    create_device,
    delete_device,
    get_device,
    get_devices,
    update_device,
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


@pytest.fixture
async def device_data() -> dict:
    return {
        "name": "テスト装置",
        "description": "テスト用の装置です",
        "location": "研究室A",
        "category": "分析機器",
    }


class TestCreateDevice:
    async def test_create_device_success(self, session: AsyncSession, device_data: dict):
        result = await create_device(session, DeviceCreate(**device_data))

        assert result.id is not None
        assert result.name == device_data["name"]
        assert result.description == device_data["description"]
        assert result.location == device_data["location"]
        assert result.category == device_data["category"]
        assert result.status == "available"
        assert result.created_at is not None
        assert result.updated_at is not None

    async def test_create_device_minimal(self, session: AsyncSession):
        result = await create_device(session, DeviceCreate(name="最小装置"))

        assert result.id is not None
        assert result.name == "最小装置"
        assert result.description is None
        assert result.location is None


class TestGetDevice:
    async def test_get_device_success(self, session: AsyncSession, device_data: dict):
        created = await create_device(session, DeviceCreate(**device_data))
        result = await get_device(session, created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == device_data["name"]

    async def test_get_device_not_found(self, session: AsyncSession):
        fake_id = uuid.uuid4()
        result = await get_device(session, fake_id)

        assert result is None


class TestGetDevices:
    async def test_get_devices_empty(self, session: AsyncSession):
        result = await get_devices(session)

        assert len(result) == 0

    async def test_get_devices_multiple(self, session: AsyncSession, device_data: dict):
        await create_device(session, DeviceCreate(**device_data))
        await create_device(session, DeviceCreate(name="装置2", location="研究室B"))

        result = await get_devices(session)

        assert len(result) == 2


class TestUpdateDevice:
    async def test_update_device_success(self, session: AsyncSession, device_data: dict):
        device = await create_device(session, DeviceCreate(**device_data))

        updated = await update_device(
            session,
            device,
            DeviceUpdate(name="更新後の装置", status="maintenance"),
        )

        assert updated.name == "更新後の装置"
        assert updated.status == "maintenance"
        assert updated.updated_at > device.created_at

    async def test_update_device_partial(self, session: AsyncSession, device_data: dict):
        device = await create_device(session, DeviceCreate(**device_data))

        updated = await update_device(session, device, DeviceUpdate(location="新的場所"))

        assert updated.name == device.name
        assert updated.location == "新的場所"


class TestDeleteDevice:
    async def test_delete_device_success(self, session: AsyncSession, device_data: dict):
        device = await create_device(session, DeviceCreate(**device_data))

        await delete_device(session, device)

        result = await get_device(session, device.id)
        assert result is None

    async def test_delete_device_with_reservations_fails(
        self, session: AsyncSession, device_data: dict
    ):
        from app.models import Reservation, User

        device = await create_device(session, DeviceCreate(**device_data))
        user = User(keycloak_id="test-user", email="test@test.com")
        session.add(user)
        await session.commit()

        reservation = Reservation(
            device_id=device.id,
            user_id=user.id,
            start_time=datetime(2026, 4, 15, 10, 0),
            end_time=datetime(2026, 4, 15, 12, 0),
        )
        session.add(reservation)
        await session.commit()

        device_id = device.id

        with pytest.raises(Exception):
            await delete_device(session, device)

        await session.rollback()
        result = await get_device(session, device_id)
        assert result is not None
