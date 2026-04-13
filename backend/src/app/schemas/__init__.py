import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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


class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None


class UserCreate(UserBase):
    keycloak_id: str
    role: str = "user"


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keycloak_id: str
    role: str
    created_at: datetime


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
