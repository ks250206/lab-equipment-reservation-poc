"""Reservation ORM → API レスポンス（ユーザー名・メールの付与）。"""

from __future__ import annotations

from .models import Reservation
from .schemas import ReservationResponse


def reservation_to_response(row: Reservation) -> ReservationResponse:
    u = row.user
    status_val = row.status.value if hasattr(row.status, "value") else str(row.status)
    return ReservationResponse(
        id=row.id,
        device_id=row.device_id,
        user_id=row.user_id,
        start_time=row.start_time,
        end_time=row.end_time,
        purpose=row.purpose,
        status=status_val,
        created_at=row.created_at,
        user_name=u.name if u is not None else None,
        user_email=u.email if u is not None else None,
    )
