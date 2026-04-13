"""JWT 検証（`decode_token`）。実キーで署名し、JWKS を引数で渡す（外部 Keycloak 不要）。"""

import base64
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwt

from app.auth import decode_token
from app.config import settings


def _int_to_base64url(val: int) -> str:
    length = (val.bit_length() + 7) // 8
    data = val.to_bytes(length, "big")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _rsa_pem_and_jwks():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-kid",
        "use": "sig",
        "n": _int_to_base64url(numbers.n),
        "e": _int_to_base64url(numbers.e),
    }
    return pem.decode("utf-8"), {"keys": [jwk]}


def _make_token(
    pem: str,
    *,
    sub: str = "kc-sub-1",
    email: str = "jwt@test.com",
    exp_offset_seconds: int = 3600,
    kid: str = "test-kid",
    aud: str | None = None,
    iss: str | None = None,
    azp: str | None = None,
) -> str:
    now = int(datetime.now(UTC).timestamp())
    aud = aud if aud is not None else settings.keycloak_client_id
    iss = iss if iss is not None else f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
    claims: dict = {
        "sub": sub,
        "email": email,
        "aud": aud,
        "iss": iss,
        "exp": now + exp_offset_seconds,
    }
    if azp is not None:
        claims["azp"] = azp
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


@pytest.mark.asyncio
async def test_decode_token_success():
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem)
    payload = await decode_token(token, jwks=jwks)
    assert payload["sub"] == "kc-sub-1"
    assert payload["email"] == "jwt@test.com"


@pytest.mark.asyncio
async def test_decode_token_success_keycloak_style_aud_and_azp():
    """Keycloak が `aud` に account のみを載せ `azp` にクライアント ID を載せる形式。"""
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem, aud="account", azp=settings.keycloak_client_id)
    payload = await decode_token(token, jwks=jwks)
    assert payload["sub"] == "kc-sub-1"


@pytest.mark.asyncio
async def test_decode_token_invalid_format():
    _pem, jwks = _rsa_pem_and_jwks()
    with pytest.raises(HTTPException) as exc:
        await decode_token("not-a-jwt", jwks=jwks)
    assert exc.value.status_code == 401
    assert "format" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_decode_token_no_matching_kid():
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem, kid="other-kid")
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, jwks=jwks)
    assert exc.value.status_code == 401
    assert "key" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_decode_token_expired():
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem, exp_offset_seconds=-60)
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, jwks=jwks)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_decode_token_wrong_audience():
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem, aud="wrong-client", azp="wrong-client")
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, jwks=jwks)
    assert exc.value.status_code == 401
    assert "mismatch" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_decode_token_wrong_issuer():
    pem, jwks = _rsa_pem_and_jwks()
    token = _make_token(pem, iss="https://evil.example/realms/x")
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, jwks=jwks)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_decode_token_bad_signature():
    _, jwks = _rsa_pem_and_jwks()
    pem_other, _ = _rsa_pem_and_jwks()
    token = _make_token(pem_other)
    with pytest.raises(HTTPException) as exc:
        await decode_token(token, jwks=jwks)
    assert exc.value.status_code == 401
