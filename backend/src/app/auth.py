import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User

security = HTTPBearer()
optional_http_bearer = HTTPBearer(auto_error=False)


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


def _jwks_rsa_key_for_kid(jwks: dict, kid: str | None) -> dict:
    """JWKS の keys から `kid` に一致する RSA 公開鍵表現を返す。見つからなければ空 dict。"""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return {}


async def get_cached_jwks(*, force_refresh: bool = False) -> dict:
    """JWKS をキャッシュする。`force_refresh` で Keycloak 鍵更新後の再取得。"""
    global _cached_jwks
    if force_refresh:
        _cached_jwks = None
    if _cached_jwks is None:
        _cached_jwks = await get_jwt_public_keys()
    return _cached_jwks


def _decode_token_with_rsa_key(token: str, rsa_key: dict) -> dict:
    try:
        return jwt.decode(
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
        ) from None
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        ) from None


async def decode_token(token: str, jwks: dict | None = None) -> dict:
    """JWT を検証する。`jwks` を渡すとネットワーク取得を行わない（テスト用）。"""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    kid = unverified_header.get("kid")
    if isinstance(kid, str):
        pass
    else:
        kid = None

    if jwks is not None:
        rsa_key = _jwks_rsa_key_for_kid(jwks, kid)
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )
        payload = _decode_token_with_rsa_key(token, rsa_key)
    else:
        jwk_data = await get_cached_jwks()
        rsa_key = _jwks_rsa_key_for_kid(jwk_data, kid)
        if not rsa_key:
            # キャッシュした JWKS と token の kid がずれる（KC 再起動・鍵ローテーション）→ 再取得
            jwk_data = await get_cached_jwks(force_refresh=True)
            rsa_key = _jwks_rsa_key_for_kid(jwk_data, kid)
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )
        payload = _decode_token_with_rsa_key(token, rsa_key)

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


def display_name_from_payload(payload: dict) -> str | None:
    for key in ("name", "preferred_username"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def me_profile_fields_from_payload(payload: dict, keycloak_id: str) -> tuple[str, str | None]:
    """JWT から `/api/users/me` 用の表示フィールドを返す。"""
    email = _safe_email_for_user(payload.get("email"), keycloak_id)
    return email, display_name_from_payload(payload)


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


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_http_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """`Authorization` があるときだけ JWT を検証し、ユーザーを返す。"""
    if credentials is None:
        return None
    payload = await decode_token(credentials.credentials)
    return await get_or_create_user_from_payload(session, payload)


async def get_or_create_user_from_payload(session: AsyncSession, payload: dict) -> User:
    keycloak_id = payload.get("sub")
    if not keycloak_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    result = await session.execute(select(User).where(User.keycloak_id == keycloak_id))
    user = result.scalar_one_or_none()

    email, disp_name = me_profile_fields_from_payload(payload, keycloak_id)

    if user is None:
        user = User(
            keycloak_id=keycloak_id,
            email=email,
            name=disp_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    changed = False
    if user.email is None:
        user.email = email
        changed = True
    if user.name is None and disp_name is not None:
        user.name = disp_name
        changed = True
    if changed:
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
