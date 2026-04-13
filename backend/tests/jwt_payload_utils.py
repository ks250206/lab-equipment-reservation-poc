"""結合テスト用: get_token_payload オーバーライド向けの JWT 相当 dict。"""

from app.config import settings


def jwt_like_payload(
    *,
    sub: str,
    realm_roles: list[str],
    email: str | None = None,
    name: str | None = None,
) -> dict:
    d: dict = {
        "sub": sub,
        "realm_access": {"roles": list(realm_roles)},
        "azp": settings.keycloak_client_id,
        "aud": "account",
    }
    if email is not None:
        d["email"] = email
    if name is not None:
        d["name"] = name
    return d
