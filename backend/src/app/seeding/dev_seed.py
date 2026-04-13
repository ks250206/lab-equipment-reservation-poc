"""開発シードの定数（装置は決定的 UUID。ユーザーは Keycloak が正で、DB 行はシードが同期）。"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from ..config import DeviceStatus, ReservationStatus

# 名前空間は固定（再実行でも同じ UUID）
SEED_NAMESPACE = uuid.UUID("6ba7b811-1111-7000-8000-000000000001")


def uid(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"user:{key}")


def did(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"device:{key}")


# Keycloak 開発シードの正: username / email / 氏名（DB 行にも email / name を同期）
# db_key … アプリ users.id 用の決定的 UUID に使う安定キー
KEYCLOAK_DEV_SEED_USER_SPECS: list[dict[str, str]] = [
    {
        "db_key": "yamada",
        "username": "seed-yamada",
        "email": "yamada.taro@example.local",
        "first_name": "太郎",
        "last_name": "山田",
    },
    {
        "db_key": "sato",
        "username": "seed-sato",
        "email": "sato.hanako@example.local",
        "first_name": "花子",
        "last_name": "佐藤",
    },
    {
        "db_key": "suzuki",
        "username": "seed-suzuki",
        "email": "suzuki.ichiro@example.local",
        "first_name": "一郎",
        "last_name": "鈴木",
    },
    {
        "db_key": "takahashi",
        "username": "seed-takahashi",
        "email": "takahashi.misaki@example.local",
        "first_name": "美咲",
        "last_name": "高橋",
    },
    {
        "db_key": "ito",
        "username": "seed-ito",
        "email": "ito.hayate@example.local",
        "first_name": "颯",
        "last_name": "伊藤",
    },
    {
        "db_key": "watanabe",
        "username": "seed-watanabe",
        "email": "watanabe.yui@example.local",
        "first_name": "結衣",
        "last_name": "渡辺",
    },
    {
        "db_key": "nakamura",
        "username": "seed-nakamura",
        "email": "nakamura.daisuke@example.local",
        "first_name": "大輔",
        "last_name": "中村",
    },
    {
        "db_key": "kobayashi",
        "username": "seed-kobayashi",
        "email": "kobayashi.sakura@example.local",
        "first_name": "さくら",
        "last_name": "小林",
    },
]


def seed_display_name(spec: dict[str, str]) -> str:
    return f"{spec['last_name']} {spec['first_name']}"


def offline_seed_user_rows() -> list[dict[str, Any]]:
    """pytest 等 Keycloak 無しで run_seed する用（JWT の sub にはならない擬似 keycloak_id）。"""
    return [
        {
            "id": uid(s["db_key"]),
            "keycloak_id": f"offline-keycloak:{s['username']}",
            "email": s["email"],
            "name": seed_display_name(s),
        }
        for s in KEYCLOAK_DEV_SEED_USER_SPECS
    ]


SEED_USER_IDS: list[uuid.UUID] = [uid(s["db_key"]) for s in KEYCLOAK_DEV_SEED_USER_SPECS]

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
_DISCONTINUED_KEYS = {("battery", 0), ("tg_dta", 1)}


def _build_device_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for slug, cat in _CATEGORIES:
        for n in range(3):
            key = f"{slug}-{n + 1}"
            status = DeviceStatus.AVAILABLE
            if (slug, n) in _UNAVAILABLE_KEYS:
                status = DeviceStatus.UNAVAILABLE
            elif (slug, n) in _DISCONTINUED_KEYS:
                status = DeviceStatus.DISCONTINUED
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
SEED_DEVICE_IDS: list[uuid.UUID] = cast(list[uuid.UUID], [d["id"] for d in DEVICE_ROWS])

# 各装置の予約件数（ページ確認用。シード実行時の UTC「当月+翌月」に分散）
RESERVATIONS_PER_DEVICE: int = 80


def _month_add_first_day(y: int, m: int, delta: int) -> datetime:
    """(y, m) の月の 1 日から delta ヶ月後の月の 1 日 0:00 UTC。"""
    zb = y * 12 + (m - 1) + delta
    ny = zb // 12
    nm = zb % 12 + 1
    return datetime(ny, nm, 1, tzinfo=UTC)


def build_reservation_seed_rows(*, at: datetime | None = None) -> list[dict[str, Any]]:
    """予約シードを `at` の属する月と翌月の全日時範囲に均等配置する（各装置 1h 枠・重複なし）。"""
    ref = at or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    else:
        ref = ref.astimezone(UTC)
    range_start = datetime(ref.year, ref.month, 1, tzinfo=UTC)
    range_end = _month_add_first_day(ref.year, ref.month, 2)
    span = range_end - range_start
    one_h = timedelta(hours=1)
    if span <= one_h:
        msg = "reservation seed window must exceed one hour"
        raise ValueError(msg)
    n = RESERVATIONS_PER_DEVICE
    step_sec = (span.total_seconds() - one_h.total_seconds()) / max(1, n - 1)
    rows: list[dict[str, Any]] = []
    for drow in DEVICE_ROWS:
        device_id = cast(uuid.UUID, drow["id"])
        for j in range(n):
            user_id = SEED_USER_IDS[j % len(SEED_USER_IDS)]
            start = range_start + timedelta(seconds=j * step_sec)
            end = start + one_h
            rid = uuid.uuid5(SEED_NAMESPACE, f"reservation:{device_id}:{j}")
            if j % 17 == 0:
                res_status = ReservationStatus.COMPLETED
            elif j % 19 == 0:
                res_status = ReservationStatus.CANCELLED
            else:
                res_status = ReservationStatus.CONFIRMED
            rows.append(
                {
                    "id": rid,
                    "device_id": device_id,
                    "user_id": user_id,
                    "start_time": start,
                    "end_time": end,
                    "purpose": f"シード予約 {j + 1}/{RESERVATIONS_PER_DEVICE}",
                    "status": res_status,
                }
            )
    return rows
