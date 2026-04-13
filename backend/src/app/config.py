from enum import StrEnum
from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class DeviceStatus(StrEnum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"


class ReservationStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/device_reservation"
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "master"
    keycloak_client_id: str = "device-reservation"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    UserRole: ClassVar[type[UserRole]] = UserRole
    DeviceStatus: ClassVar[type[DeviceStatus]] = DeviceStatus
    ReservationStatus: ClassVar[type[ReservationStatus]] = ReservationStatus

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
