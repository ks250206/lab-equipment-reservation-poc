from datetime import UTC, datetime, timedelta, timezone

from app.datetime_util import ensure_utc


def test_ensure_utc_naive_is_utc():
    naive = datetime(2026, 4, 15, 10, 0)
    out = ensure_utc(naive)
    assert out.tzinfo == UTC
    assert out.replace(tzinfo=None) == naive


def test_ensure_utc_aware_converts_to_utc():
    jst = timezone(timedelta(hours=9))
    aware = datetime(2026, 4, 15, 19, 0, tzinfo=jst)
    out = ensure_utc(aware)
    assert out.tzinfo == UTC
    assert out == datetime(2026, 4, 15, 10, 0, tzinfo=UTC)
