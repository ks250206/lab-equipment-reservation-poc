import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import UserRole, settings
from .db import get_session
from .models import User

security = HTTPBearer()


def _access_token_allows_client(payload: dict, client_id: str) -> bool:
    """Keycloak の access token は aud が account、azp がクライアント ID であることが多い。"""
    if payload.get("azp") == client_id:
        return True
    aud = payload.get("aud")
    if aud == client_id:
        return True
    if isinstance(aud, list) and client_id in aud:
        return True
    return False


async def get_jwt_public_keys() -> dict:
    jwks_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        return response.json()


_cached_jwks: dict | None = None


async def get_cached_jwks() -> dict:
    global _cached_jwks
    if _cached_jwks is None:
        _cached_jwks = await get_jwt_public_keys()
    return _cached_jwks


async def decode_token(token: str, jwks: dict | None = None) -> dict:
    """JWT を検証する。`jwks` を渡すとネットワーク取得を行わない（テスト用）。"""
    if jwks is None:
        jwks = await get_cached_jwks()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    rsa_key = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key",
        )

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer=f"{settings.keycloak_url}/realms/{settings.keycloak_realm}",
            options={"verify_aud": False},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    if not _access_token_allows_client(payload, settings.keycloak_client_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=("Invalid token: client mismatch (expected azp or aud to match API client id)"),
        )

    return payload


def realm_roles_from_payload(payload: dict) -> set[str]:
    """Keycloak access token の realm_access.roles を集合で返す。"""
    ra = payload.get("realm_access")
    if not isinstance(ra, dict):
        return set()
    roles = ra.get("roles")
    if not isinstance(roles, list):
        return set()
    out: set[str] = set()
    for x in roles:
        if isinstance(x, str):
            out.add(x)
    return out


def is_app_admin_from_payload(payload: dict) -> bool:
    """アプリ管理者: レルムロール名が設定値と一致するか（Keycloak が正）。"""
    return settings.keycloak_app_admin_realm_role in realm_roles_from_payload(payload)


def _safe_email_for_user(raw: object, keycloak_id: str) -> str:
    """JWT の email が欠落・非 RFC のときに DB とレスポンス検証を壊さない。"""
    placeholder = f"{keycloak_id}@unknown.local"
    if raw is None or not isinstance(raw, str):
        return placeholder
    s = raw.strip()
    if not s:
        return placeholder
    try:
        TypeAdapter(EmailStr).validate_python(s)
        return s
    except Exception:
        return placeholder


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """検証済み JWT ペイロード（同一リクエスト内で複数 Depends しても再検証はキャッシュされる）。"""
    return await decode_token(credentials.credentials)


async def get_current_user(
    payload: dict = Depends(get_token_payload),
    session: AsyncSession = Depends(get_session),
) -> User:
    return await get_or_create_user_from_payload(session, payload)


async def get_or_create_user_from_payload(session: AsyncSession, payload: dict) -> User:
    keycloak_id = payload.get("sub")
    if not keycloak_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    email = _safe_email_for_user(payload.get("email"), keycloak_id)
    name = payload.get("name")

    result = await session.execute(select(User).where(User.keycloak_id == keycloak_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            keycloak_id=keycloak_id,
            email=email,
            name=name,
            role=UserRole.USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def require_admin(
    _user: User = Depends(get_current_user),
    payload: dict = Depends(get_token_payload),
) -> User:
    if not is_app_admin_from_payload(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return _user
