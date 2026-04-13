"""装置画像バイト列の検証（マジックバイトの粗判定 + Pillow で実画像として検証）。"""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from ..config import get_settings


def validate_device_image_bytes(content: bytes) -> str:
    """PNG または JPEG の実ファイルのみ許可。戻り値は `Content-Type` 用の MIME。"""
    settings = get_settings()
    max_b = settings.device_image_max_bytes
    if len(content) > max_b:
        msg = f"画像サイズが上限（{max_b} バイト）を超えています"
        raise ValueError(msg)
    if len(content) < 9:
        msg = "画像データが短すぎます"
        raise ValueError(msg)
    if not (content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\xff\xd8\xff")):
        msg = "PNG または JPEG のみアップロードできます（先頭バイトが一致しません）"
        raise ValueError(msg)
    try:
        with Image.open(BytesIO(content)) as im:
            im.verify()
        with Image.open(BytesIO(content)) as im:
            fmt = im.format
    except (UnidentifiedImageError, OSError) as e:
        msg = f"画像として解釈できません: {e}"
        raise ValueError(msg) from e
    if fmt == "PNG":
        return "image/png"
    if fmt == "JPEG":
        return "image/jpeg"
    msg = f"PNG または JPEG のみ対応です（検出形式: {fmt!r}）"
    raise ValueError(msg)
