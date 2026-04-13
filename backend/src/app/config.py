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
    DISCONTINUED = "discontinued"


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
    # JWT realm_access.roles に含まれると API の管理者とみなすレルムロール名（Keycloak 側で付与）
    keycloak_app_admin_realm_role: str = Field(
        default="app-admin",
        validation_alias=AliasChoices("KEYCLOAK_APP_ADMIN_REALM_ROLE"),
    )
    # 開発シード: このユーザー名のレルムユーザーに app-admin を付与（既定: Keycloak の admin）
    keycloak_seed_grant_app_admin_username: str = Field(
        default="admin",
        validation_alias=AliasChoices("KEYCLOAK_SEED_GRANT_APP_ADMIN_USERNAME"),
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
    # 開発シードが Keycloak に作成するダミー利用者のパスワード（全員同一。PoC 用）
    keycloak_seed_user_password: str = Field(
        default="SeedUsersDev1!",
        validation_alias=AliasChoices("KEYCLOAK_SEED_USER_PASSWORD"),
        repr=False,
    )
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # MinIO / S3 互換（装置画像）。未起動時はアップロード・シード画像がスキップされる。
    minio_endpoint_url: str = Field(
        default="http://localhost:9000",
        validation_alias=AliasChoices("MINIO_ENDPOINT_URL", "S3_ENDPOINT_URL"),
    )
    minio_access_key: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices("MINIO_ACCESS_KEY", "AWS_ACCESS_KEY_ID"),
    )
    minio_secret_key: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices("MINIO_SECRET_KEY", "AWS_SECRET_ACCESS_KEY"),
        repr=False,
    )
    minio_bucket: str = Field(
        default="device-images",
        validation_alias=AliasChoices("MINIO_BUCKET", "S3_BUCKET"),
    )
    minio_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("MINIO_REGION", "AWS_DEFAULT_REGION"),
    )
    device_image_max_bytes: int = Field(
        default=2_097_152,
        validation_alias=AliasChoices("DEVICE_IMAGE_MAX_BYTES"),
        description="装置画像 1 ファイルあたりの上限バイト数（既定 2MiB）",
    )

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
