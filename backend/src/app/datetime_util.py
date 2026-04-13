from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Naive datetime を UTC として扱い、aware は UTC に正規化する。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
