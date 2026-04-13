"""結合テスト用: get_token_payload オーバーライド向けの JWT 相当 dict。"""

from app.config import settings


def jwt_like_payload(*, sub: str, realm_roles: list[str]) -> dict:
    return {
        "sub": sub,
        "realm_access": {"roles": list(realm_roles)},
        "azp": settings.keycloak_client_id,
        "aud": "account",
    }
