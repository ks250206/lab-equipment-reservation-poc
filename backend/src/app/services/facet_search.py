from collections import Counter
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DeviceStatus
from ..models import Device


async def search_devices(
    session: AsyncSession,
    q: str | None = None,
    category: str | None = None,
    location: str | None = None,
    status: DeviceStatus | None = None,
) -> Sequence[Device]:
    query = select(Device)

    conditions = []
    if q:
        search_pattern = f"%{q}%"
        conditions.append(
            or_(
                Device.name.ilike(search_pattern),
                Device.description.ilike(search_pattern),
                Device.location.ilike(search_pattern),
                Device.category.ilike(search_pattern),
            )
        )
    if category:
        conditions.append(Device.category == category)
    if location:
        conditions.append(Device.location == location)
    if status:
        conditions.append(Device.status == status)

    if conditions:
        query = query.where(*conditions)

    result = await session.execute(query)
    return result.scalars().all()


async def get_facets(
    session: AsyncSession,
    q: str | None = None,
) -> dict:
    base_query = select(Device)

    if q:
        search_pattern = f"%{q}%"
        base_query = base_query.where(
            or_(
                Device.name.ilike(search_pattern),
                Device.description.ilike(search_pattern),
                Device.location.ilike(search_pattern),
                Device.category.ilike(search_pattern),
            )
        )

    result = await session.execute(base_query)
    devices = result.scalars().all()

    categories = [d.category for d in devices if d.category]
    locations = [d.location for d in devices if d.location]
    statuses = [d.status.value for d in devices]

    facets = {
        "category": [
            {"value": value, "count": count} for value, count in Counter(categories).most_common()
        ],
        "location": [
            {"value": value, "count": count} for value, count in Counter(locations).most_common()
        ],
        "status": [
            {"value": value, "count": count} for value, count in Counter(statuses).most_common()
        ],
    }

    return facets


async def get_all_categories(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Device.category).where(Device.category.isnot(None)).distinct()
    )
    return [row[0] for row in result.all()]


async def get_all_locations(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Device.location).where(Device.location.isnot(None)).distinct()
    )
    return [row[0] for row in result.all()]
