from enum import StrEnum
from functools import lru_cache
from typing import ClassVar

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    """環境変数 ENVIRONMENT / APP_ENV で development | production を切替（既定: development）。"""

    database_url: str = (
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/device_reservation"
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "master"
    keycloak_client_id: str = "device-reservation"
    # カンマ区切りの preferred_username。初回 DB 登録時のみ role=admin（既存行は変えない）
    keycloak_bootstrap_admin_usernames: str = Field(
        default="",
        validation_alias=AliasChoices("KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES"),
    )
    # 開発シード（Keycloak Admin API）用。compose の KEYCLOAK_ADMIN と揃えることが多い。
    keycloak_seed_admin_username: str = Field(
        default="admin",
        validation_alias=AliasChoices("KEYCLOAK_SEED_ADMIN_USERNAME"),
    )
    keycloak_seed_admin_password: str = Field(
        default="admin",
        validation_alias=AliasChoices("KEYCLOAK_SEED_ADMIN_PASSWORD"),
        repr=False,
    )
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "development"
        s = str(v).strip().lower()
        if s in ("dev", "development"):
            return "development"
        if s in ("prod", "production"):
            return "production"
        raise ValueError(f"ENVIRONMENT は development または production です: {v!r}")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    UserRole: ClassVar[type[UserRole]] = UserRole
    DeviceStatus: ClassVar[type[DeviceStatus]] = DeviceStatus
    ReservationStatus: ClassVar[type[ReservationStatus]] = ReservationStatus

    model_config = SettingsConfigDict(
        # backend/ から起動してもリポジトリルートの .env を拾う
        env_file=(".env", "../.env"),
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
