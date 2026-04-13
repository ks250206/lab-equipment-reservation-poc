"""開発シードの定数（決定的 UUID で冪等に upsert）。"""

import uuid
from typing import cast

from ..config import DeviceStatus, UserRole

# 名前空間は固定（再実行でも同じ UUID）
SEED_NAMESPACE = uuid.UUID("6ba7b811-1111-7000-8000-000000000001")


def uid(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"user:{key}")


def did(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"device:{key}")


SEED_USERS: list[dict[str, object]] = [
    {
        "id": uid("yamada"),
        "keycloak_id": "seed-yamada-taro",
        "email": "yamada.taro@example.local",
        "name": "山田 太郎",
        "role": UserRole.ADMIN,
    },
    {
        "id": uid("sato"),
        "keycloak_id": "seed-sato-hanako",
        "email": "sato.hanako@example.local",
        "name": "佐藤 花子",
        "role": UserRole.USER,
    },
    {
        "id": uid("suzuki"),
        "keycloak_id": "seed-suzuki-ichiro",
        "email": "suzuki.ichiro@example.local",
        "name": "鈴木 一郎",
        "role": UserRole.USER,
    },
    {
        "id": uid("takahashi"),
        "keycloak_id": "seed-takahashi-misaki",
        "email": "takahashi.misaki@example.local",
        "name": "高橋 美咲",
        "role": UserRole.USER,
    },
    {
        "id": uid("ito"),
        "keycloak_id": "seed-ito-hayate",
        "email": "ito.hayate@example.local",
        "name": "伊藤 颯",
        "role": UserRole.USER,
    },
    {
        "id": uid("watanabe"),
        "keycloak_id": "seed-watanabe-yui",
        "email": "watanabe.yui@example.local",
        "name": "渡辺 結衣",
        "role": UserRole.USER,
    },
    {
        "id": uid("nakamura"),
        "keycloak_id": "seed-nakamura-daisuke",
        "email": "nakamura.daisuke@example.local",
        "name": "中村 大輔",
        "role": UserRole.USER,
    },
    {
        "id": uid("kobayashi"),
        "keycloak_id": "seed-kobayashi-sakura",
        "email": "kobayashi.sakura@example.local",
        "name": "小林 さくら",
        "role": UserRole.USER,
    },
]

_CATEGORIES: list[tuple[str, str]] = [
    ("xrd", "XRD"),
    ("xrf", "XRF"),
    ("xps", "XPS"),
    ("battery", "充放電装置"),
    ("tg_dta", "TG-DTA"),
    ("glove", "グローブボックス"),
    ("sem", "SEM"),
    ("print3d", "3Dプリンタ"),
    ("evap", "蒸着装置"),
    ("sputter", "スパッタ装置"),
    ("ion_mill", "イオンミリング装置"),
]

_LABS = ("計測室A", "計測室B", "共用ラボ")
_FLOORS = ("材料棟 1F", "材料棟 2F", "実験棟 3F")
# 一部だけメンテ・利用不可にして一覧のバリエーションを付ける
_MAINTENANCE_KEYS = {("sem", 2), ("xps", 0), ("print3d", 1)}
_UNAVAILABLE_KEYS = {("ion_mill", 2)}


def _build_device_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for slug, cat in _CATEGORIES:
        for n in range(3):
            key = f"{slug}-{n + 1}"
            status = DeviceStatus.AVAILABLE
            if (slug, n) in _UNAVAILABLE_KEYS:
                status = DeviceStatus.UNAVAILABLE
            elif (slug, n) in _MAINTENANCE_KEYS:
                status = DeviceStatus.MAINTENANCE
            rows.append(
                {
                    "id": did(key),
                    "name": f"{cat}／{_LABS[n]}（ユニット{n + 1}）",
                    "description": f"{cat}向けの PoC シード。[bench:{slug}]",
                    "location": f"{_FLOORS[n]} {_LABS[n]}",
                    "category": cat,
                    "status": status,
                }
            )
    return rows


DEVICE_ROWS: list[dict[str, object]] = _build_device_rows()
SEED_USER_IDS: list[uuid.UUID] = cast(list[uuid.UUID], [u["id"] for u in SEED_USERS])
SEED_DEVICE_IDS: list[uuid.UUID] = cast(list[uuid.UUID], [d["id"] for d in DEVICE_ROWS])
