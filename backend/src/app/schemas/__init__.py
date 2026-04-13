import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    category: str | None = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    category: str | None = None
    status: str | None = None


class DeviceResponse(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    has_image: bool = False
    is_favorite: bool = False


def device_to_response(device: object, *, is_favorite: bool = False) -> DeviceResponse:
    """ORM `Device` から `has_image` / `is_favorite` を埋めてレスポンスを組み立てる。"""
    from ..models import Device as DeviceModel

    if not isinstance(device, DeviceModel):
        msg = f"Device 以外は渡せません: {type(device)!r}"
        raise TypeError(msg)
    status_val = device.status.value if hasattr(device.status, "value") else str(device.status)
    return DeviceResponse(
        id=device.id,
        name=device.name,
        description=device.description,
        location=device.location,
        category=device.category,
        status=status_val,
        created_at=device.created_at,
        updated_at=device.updated_at,
        has_image=device.image_object_key is not None,
        is_favorite=is_favorite,
    )


class PaginatedDeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    total: int
    page: int
    page_size: int


class UserCreate(BaseModel):
    """テスト等用。HTTP では未使用。"""

    keycloak_id: str


class UserResponse(BaseModel):
    """管理者向け一覧・詳細。アプリ DB に保持している列のみ。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keycloak_id: str
    created_at: datetime


class UserMeResponse(UserResponse):
    """ログイン中ユーザー。email / name / role は JWT 由来（role は管理者ロールの有無）。"""

    email: str
    name: str | None = None
    role: str


class ReservationCreate(BaseModel):
    """API 予約作成。利用者は JWT から解決するため user_id は含めない。"""

    device_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    purpose: str | None = None


class ReservationUpdate(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    purpose: str | None = None
    status: str | None = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    user_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    purpose: str | None = None
    status: str
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None


class PaginatedReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    total: int
    page: int
    page_size: int
