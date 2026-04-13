"""Keycloak シード用ヘルパの単体テスト（HTTP は使わない）。"""

from app.seeding.keycloak_seed import (
    _apply_spa_fields,
    _clients_matching_client_id,
    _post_logout_uris_attr,
)


def test_post_logout_uris_joins_with_hash_pair():
    s = _post_logout_uris_attr()
    assert "http://localhost:5173/*" in s
    assert "##" in s


def test_clients_matching_client_id_exact_only():
    raw = [
        {"id": "a", "clientId": "account"},
        {"id": "b", "clientId": "device-reservation"},
    ]
    m = _clients_matching_client_id(raw, "device-reservation")
    assert len(m) == 1
    assert m[0]["id"] == "b"


def test_clients_matching_ignores_non_dict_and_partial_client_id():
    raw: list = [
        {"id": "a", "clientId": "device-reservation-wrong"},
        12,
        "x",
        {},
    ]
    assert _clients_matching_client_id(raw, "device-reservation") == []


def test_apply_spa_fields_public_client_and_redirects():
    body = _apply_spa_fields({"clientId": "device-reservation", "enabled": True})
    assert body["publicClient"] is True
    assert body["standardFlowEnabled"] is True
    assert body["directAccessGrantsEnabled"] is False
    assert "http://localhost:5173/*" in body["redirectUris"]
    assert body["attributes"]["pkce.code.challenge.method"] == "S256"
