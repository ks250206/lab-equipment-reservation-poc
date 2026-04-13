"""装置画像の S3 互換 API（MinIO 想定）。"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ..config import get_settings

if TYPE_CHECKING:
    pass


def _client() -> BaseClient:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.minio_endpoint_url,
        aws_access_key_id=s.minio_access_key,
        aws_secret_access_key=s.minio_secret_key,
        region_name=s.minio_region,
    )


def ensure_device_images_bucket() -> None:
    s = get_settings()
    c = _client()
    try:
        c.head_bucket(Bucket=s.minio_bucket)
    except ClientError:
        c.create_bucket(Bucket=s.minio_bucket)


def put_device_image_object(*, device_id: uuid.UUID, body: bytes, content_type: str) -> str:
    """オブジェクトを保存し、キーを返す（上書き用に UUID サフィックス）。"""
    s = get_settings()
    ext = "png" if content_type == "image/png" else "jpg"
    key = f"devices/{device_id}/{uuid.uuid4()}.{ext}"
    c = _client()
    c.put_object(
        Bucket=s.minio_bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return key


def get_device_image_bytes(*, object_key: str) -> tuple[bytes, str]:
    """(body, content_type) を返す。オブジェクトが無いときは ClientError。"""
    s = get_settings()
    c = _client()
    o = c.get_object(Bucket=s.minio_bucket, Key=object_key)
    body: bytes = o["Body"].read()
    ct = str(o.get("ContentType") or "application/octet-stream")
    return body, ct


def delete_device_image_object(*, object_key: str | None) -> None:
    if not object_key:
        return
    s = get_settings()
    c = _client()
    try:
        c.delete_object(Bucket=s.minio_bucket, Key=object_key)
    except ClientError:
        pass
