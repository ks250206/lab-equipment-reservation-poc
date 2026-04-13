"""オブジェクトストレージ（MinIO / S3 互換）。"""

from .s3_device_images import (
    delete_device_image_object,
    ensure_device_images_bucket,
    get_device_image_bytes,
    put_device_image_object,
)

__all__ = [
    "delete_device_image_object",
    "ensure_device_images_bucket",
    "get_device_image_bytes",
    "put_device_image_object",
]
