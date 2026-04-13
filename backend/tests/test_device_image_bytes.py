import base64
from io import BytesIO

import pytest
from PIL import Image

from app.services.device_image_bytes import validate_device_image_bytes

_MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_validate_accepts_png():
    assert validate_device_image_bytes(_MINI_PNG) == "image/png"


def test_validate_accepts_jpeg_from_pil():
    buf = BytesIO()
    Image.new("RGB", (2, 2), color=(200, 100, 50)).save(buf, format="JPEG", quality=90)
    raw = buf.getvalue()
    assert validate_device_image_bytes(raw) == "image/jpeg"


def test_validate_rejects_gif():
    with pytest.raises(ValueError, match="先頭バイト"):
        validate_device_image_bytes(b"GIF89a" + b"\x00" * 40)


def test_validate_rejects_jpeg_magic_only_garbage():
    with pytest.raises(ValueError, match="解釈できません"):
        validate_device_image_bytes(b"\xff\xd8\xff" + b"\x00" * 200)


def test_validate_rejects_oversize(monkeypatch):
    from app.config import Settings

    class _S(Settings):
        device_image_max_bytes: int = 10

    monkeypatch.setattr("app.services.device_image_bytes.get_settings", lambda: _S())
    with pytest.raises(ValueError, match="上限"):
        validate_device_image_bytes(_MINI_PNG)
