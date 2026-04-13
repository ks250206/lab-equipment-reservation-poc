import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DeviceStatus, settings
from app.db import Base
from app.models import Device
from app.services.facet_search import (
    get_all_categories,
    get_all_locations,
    get_facets,
    search_devices,
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


class TestSearchDevices:
    async def test_search_all_devices(self, session: AsyncSession):
        device1 = Device(
            name="装置A", location="研究室A", category="分析機器", status=DeviceStatus.AVAILABLE
        )
        device2 = Device(
            name="装置B", location="研究室B", category="測定機器", status=DeviceStatus.MAINTENANCE
        )
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session)
        assert len(result) == 2

    async def test_search_by_name(self, session: AsyncSession):
        device1 = Device(name="電子顕微鏡", location="研究室A", category="分析機器")
        device2 = Device(name="分光計", location="研究室B", category="測定機器")
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, q="電子")
        assert len(result) == 1
        assert result[0].name == "電子顕微鏡"

    async def test_search_by_description(self, session: AsyncSession):
        device1 = Device(name="装置A", description="高精度の測定が可能", location="研究室A")
        device2 = Device(name="装置B", description="基本的な機能", location="研究室B")
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, q="高精度")
        assert len(result) == 1

    async def test_filter_by_category(self, session: AsyncSession):
        device1 = Device(name="装置A", category="分析機器")
        device2 = Device(name="装置B", category="測定機器")
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, category="分析機器")
        assert len(result) == 1
        assert result[0].category == "分析機器"

    async def test_filter_by_location(self, session: AsyncSession):
        device1 = Device(name="装置A", location="研究室A")
        device2 = Device(name="装置B", location="研究室B")
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, location="研究室A")
        assert len(result) == 1
        assert result[0].location == "研究室A"

    async def test_filter_by_status(self, session: AsyncSession):
        device1 = Device(name="装置A", status=DeviceStatus.AVAILABLE)
        device2 = Device(name="装置B", status=DeviceStatus.MAINTENANCE)
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, status=DeviceStatus.AVAILABLE)
        assert len(result) == 1
        assert result[0].status == DeviceStatus.AVAILABLE

    async def test_combined_filter(self, session: AsyncSession):
        device1 = Device(
            name="装置A", location="研究室A", category="分析機器", status=DeviceStatus.AVAILABLE
        )
        device2 = Device(
            name="装置B", location="研究室B", category="測定機器", status=DeviceStatus.MAINTENANCE
        )
        session.add_all([device1, device2])
        await session.commit()

        result = await search_devices(session, location="研究室A", status=DeviceStatus.AVAILABLE)
        assert len(result) == 1


class TestGetFacets:
    async def test_get_facets_all(self, session: AsyncSession):
        device1 = Device(
            name="装置A", location="研究室A", category="分析機器", status=DeviceStatus.AVAILABLE
        )
        device2 = Device(
            name="装置B", location="研究室A", category="分析機器", status=DeviceStatus.MAINTENANCE
        )
        device3 = Device(
            name="装置C", location="研究室B", category="測定機器", status=DeviceStatus.AVAILABLE
        )
        session.add_all([device1, device2, device3])
        await session.commit()

        facets = await get_facets(session)

        assert len(facets["category"]) == 2
        assert len(facets["location"]) == 2
        assert len(facets["status"]) == 2

    async def test_get_facets_with_search(self, session: AsyncSession):
        device1 = Device(name="電子顕微鏡", location="研究室A", category="分析機器")
        device2 = Device(name="光学顕微鏡", location="研究室A", category="分析機器")
        device3 = Device(name="分光計", location="研究室B", category="測定機器")
        session.add_all([device1, device2, device3])
        await session.commit()

        facets = await get_facets(session, q="顕微鏡")

        assert len(facets["category"]) == 1
        assert facets["category"][0]["value"] == "分析機器"
        assert facets["category"][0]["count"] == 2

    async def test_get_facets_empty(self, session: AsyncSession):
        facets = await get_facets(session)
        assert facets["category"] == []
        assert facets["location"] == []
        assert facets["status"] == []


class TestGetAllCategories:
    async def test_get_all_categories(self, session: AsyncSession):
        device1 = Device(name="装置A", category="分析機器")
        device2 = Device(name="装置B", category="測定機器")
        device3 = Device(name="装置C", category=None)
        session.add_all([device1, device2, device3])
        await session.commit()

        categories = await get_all_categories(session)
        assert len(categories) == 2
        assert "分析機器" in categories
        assert "測定機器" in categories


class TestGetAllLocations:
    async def test_get_all_locations(self, session: AsyncSession):
        device1 = Device(name="装置A", location="研究室A")
        device2 = Device(name="装置B", location="研究室B")
        device3 = Device(name="装置C", location=None)
        session.add_all([device1, device2, device3])
        await session.commit()

        locations = await get_all_locations(session)
        assert len(locations) == 2
        assert "研究室A" in locations
        assert "研究室B" in locations
