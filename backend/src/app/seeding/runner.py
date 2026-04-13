"""開発シード実行（PostgreSQL 上で冪等 upsert）。"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from sqlalchemy import delete, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ..config import Settings
from ..db import async_session_factory, init_db
from ..models import Device, Reservation, User
from .dev_seed import DEVICE_ROWS, SEED_DEVICE_IDS, SEED_USER_IDS, build_reservation_seed_rows
from .device_image_seed import seed_device_images_after_devices
from .keycloak_seed import (
    ensure_keycloak_app_admin_realm_role,
    ensure_keycloak_dev_seed_users,
    ensure_keycloak_equipment_reservation_client,
)


def ensure_development_for_seed() -> None:
    # モジュールの `settings` は import 時に固定されるため、CLI 用に毎回環境を読む
    if Settings().is_production:
        raise RuntimeError(
            "開発シードは ENVIRONMENT=development のときのみ実行できます（現在: production）。"
        )


async def run_seed(
    *,
    user_rows: list[dict[str, object]],
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    ensure_development_for_seed()
    factory = session_factory or async_session_factory
    async with factory() as _bind_probe:
        bind = _bind_probe.bind
    if isinstance(bind, AsyncEngine):
        await init_db(bind)
    elif bind is None:
        await init_db()
    else:
        msg = f"想定外の Session.bind 型です: {type(bind)!r}"
        raise RuntimeError(msg)
    async with factory() as session:
        async with session.begin():
            await session.execute(
                delete(Reservation).where(
                    or_(
                        Reservation.device_id.in_(SEED_DEVICE_IDS),
                        Reservation.user_id.in_(SEED_USER_IDS),
                    )
                )
            )
            await session.execute(delete(User).where(User.id.in_(SEED_USER_IDS)))
            for row in user_rows:
                ins_u = pg_insert(User).values(**row)
                ins_u = ins_u.on_conflict_do_update(
                    index_elements=[User.id],
                    set_={
                        "keycloak_id": ins_u.excluded.keycloak_id,
                        "email": ins_u.excluded.email,
                        "name": ins_u.excluded.name,
                    },
                )
                await session.execute(ins_u)
            for row in DEVICE_ROWS:
                ins = pg_insert(Device).values(**row)
                ins = ins.on_conflict_do_update(
                    index_elements=[Device.id],
                    set_={
                        "name": ins.excluded.name,
                        "description": ins.excluded.description,
                        "location": ins.excluded.location,
                        "category": ins.excluded.category,
                        "status": ins.excluded.status,
                    },
                )
                await session.execute(ins)
            res_rows = build_reservation_seed_rows(at=datetime.now(UTC))
            for i in range(0, len(res_rows), 400):
                chunk = res_rows[i : i + 400]
                session.add_all([Reservation(**row) for row in chunk])

    await seed_device_images_after_devices(factory)


async def _run_seed_and_keycloak() -> str:
    cfg = Settings()
    user_rows, user_msg = await ensure_keycloak_dev_seed_users(cfg)
    if not user_rows:
        raise RuntimeError(user_msg)
    await run_seed(user_rows=user_rows)
    line1 = await ensure_keycloak_equipment_reservation_client(cfg)
    line2 = await ensure_keycloak_app_admin_realm_role(cfg)
    return f"{user_msg}\n{line1}\n{line2}"


def main() -> None:
    try:
        kc_line = asyncio.run(_run_seed_and_keycloak())
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print("開発シードを反映しました（Keycloak ユーザー → users / devices）。")
    print(kc_line)
