"""開発シード用: Keycloak Admin API で SPA クライアントを冪等に作成・更新する。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)

# フロント既定（Vite / preview）と doc/keycloak-setup.md に合わせる
DEFAULT_REDIRECT_URIS = (
    "http://localhost:5173/*",
    "http://localhost:4173/*",
)
DEFAULT_WEB_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:4173",
)


def _post_logout_uris_attr() -> str:
    return "##".join(DEFAULT_REDIRECT_URIS)


def _clients_matching_client_id(raw: list[Any], client_id: str) -> list[dict[str, Any]]:
    """一覧応答がクエリ無視のときがあるため、clientId 完全一致の行だけを採用する。"""
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("clientId") == client_id:
            out.append(item)
    return out


def _keycloak_client() -> httpx.AsyncClient:
    # HTTP/2 や接続先の挙動で切断されやすいケースを避ける
    return httpx.AsyncClient(
        http2=False,
        timeout=httpx.Timeout(60.0, connect=15.0),
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    )


def _apply_spa_fields(body: dict[str, Any]) -> dict[str, Any]:
    """既存クライアント JSON に PoC 用の SPA 設定を上書きする。"""
    out = dict(body)
    out["clientId"] = out.get("clientId") or "device-reservation"
    out["publicClient"] = True
    out["protocol"] = "openid-connect"
    out["standardFlowEnabled"] = True
    out["implicitFlowEnabled"] = False
    out["directAccessGrantsEnabled"] = False
    out["bearerOnly"] = False
    out["redirectUris"] = list(DEFAULT_REDIRECT_URIS)
    out["webOrigins"] = list(DEFAULT_WEB_ORIGINS)
    attrs = dict(out.get("attributes") or {})
    attrs["pkce.code.challenge.method"] = "S256"
    attrs["post.logout.redirect.uris"] = _post_logout_uris_attr()
    out["attributes"] = attrs
    return out


async def _admin_token(
    client: httpx.AsyncClient,
    base: str,
    username: str,
    password: str,
) -> str:
    url = f"{base}/realms/master/protocol/openid-connect/token"
    r = await client.post(
        url,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15.0,
    )
    r.raise_for_status()
    data = r.json()
    token = data.get("access_token")
    if not isinstance(token, str):
        raise RuntimeError("Keycloak: 管理トークン応答に access_token がありません")
    return token


async def ensure_keycloak_device_reservation_client(settings: Settings) -> str:
    """
    Keycloak の `settings.keycloak_client_id` を公開クライアントとして冪等に揃える。

    Keycloak が未起動・未到達のときは接続エラーを握りつぶし、メッセージのみ返す。
    """
    base = settings.keycloak_url.rstrip("/")
    realm = settings.keycloak_realm
    cid = settings.keycloak_client_id
    user = settings.keycloak_seed_admin_username
    pw = settings.keycloak_seed_admin_password

    try:
        async with _keycloak_client() as client:
            token = await _admin_token(client, base, user, pw)
            headers = {"Authorization": f"Bearer {token}"}

            list_url = f"{base}/admin/realms/{realm}/clients"
            # max=-1: 既定の 100 件切りで取りこぼさない。応答は必ず clientId で絞り込む。
            lr = await client.get(
                list_url,
                params={"clientId": cid, "max": "-1"},
                headers=headers,
            )
            lr.raise_for_status()
            raw_list = lr.json()
            if not isinstance(raw_list, list):
                raise RuntimeError("Keycloak: クライアント一覧の応答形式が不正です")

            matches = _clients_matching_client_id(raw_list, cid)
            logger.info(
                "Keycloak シード: realm=%s clientId=%s API件数=%s 一致件数=%s",
                realm,
                cid,
                len(raw_list),
                len(matches),
            )

            if not matches:
                rep = _apply_spa_fields({"clientId": cid, "enabled": True})
                cr = await client.post(list_url, headers=headers, json=rep)
                if cr.status_code == 409:
                    logger.warning(
                        "Keycloak シード: 作成が 409 のため再取得して更新します（clientId=%s）",
                        cid,
                    )
                    lr2 = await client.get(
                        list_url,
                        params={"clientId": cid, "max": "-1"},
                        headers=headers,
                    )
                    lr2.raise_for_status()
                    raw2 = lr2.json()
                    if not isinstance(raw2, list):
                        raise RuntimeError("Keycloak: 再取得の応答形式が不正です")
                    matches = _clients_matching_client_id(raw2, cid)
                    if not matches:
                        return (
                            f"Keycloak: クライアント「{cid}」の作成に失敗しました（409）。"
                            " 管理コンソールで重複や権限を確認してください。"
                        )
                elif cr.status_code not in (200, 201):
                    cr.raise_for_status()
                else:
                    return (
                        f"Keycloak: クライアント「{cid}」を新規作成しました"
                        "（公開クライアント・PKCE S256）。"
                    )

            internal_id = matches[0].get("id")
            if not isinstance(internal_id, str):
                raise RuntimeError("Keycloak: 一致クライアントに id がありません")

            gr = await client.get(
                f"{base}/admin/realms/{realm}/clients/{internal_id}",
                headers=headers,
            )
            gr.raise_for_status()
            merged = _apply_spa_fields(gr.json())
            pr = await client.put(
                f"{base}/admin/realms/{realm}/clients/{internal_id}",
                headers=headers,
                json=merged,
            )
            pr.raise_for_status()
            return (
                f"Keycloak: クライアント「{cid}」を冪等更新しました"
                "（公開クライアント・リダイレクト URI 等）。"
            )

    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.text[:500]
        except Exception:
            pass
        logger.warning("Keycloak シード: HTTP エラー %s %s", e.response.status_code, detail)
        return (
            f"Keycloak: 自動設定をスキップしました（HTTP {e.response.status_code}）。"
            " 管理コンソールで手動設定するか、管理者認証情報（KEYCLOAK_SEED_*）を確認してください。"
        )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("Keycloak シード: 接続不可 %s", e)
        return (
            "Keycloak: 未起動のため自動設定をスキップしました（`just deps-up` 後に再実行可能）。"
            " 手動手順は doc/keycloak-setup.md を参照してください。"
        )
    except Exception as e:
        logger.warning("Keycloak シード: 失敗 %s", e)
        return f"Keycloak: 自動設定をスキップしました（{e}）。"


async def ensure_keycloak_app_admin_realm_role(settings: Settings) -> str:
    """
    レルムロール（既定名 app-admin）を冪等に作成し、既定ユーザーにマッピングする。

    Keycloak が未到達のときは接続エラーを握りつぶし、メッセージのみ返す。
    """
    from urllib.parse import quote

    base = settings.keycloak_url.rstrip("/")
    realm = settings.keycloak_realm
    role_name = settings.keycloak_app_admin_realm_role
    grant_username = settings.keycloak_seed_grant_app_admin_username
    user = settings.keycloak_seed_admin_username
    pw = settings.keycloak_seed_admin_password

    try:
        async with _keycloak_client() as client:
            token = await _admin_token(client, base, user, pw)
            headers = {"Authorization": f"Bearer {token}"}
            roles_base = f"{base}/admin/realms/{realm}/roles"

            gr = await client.get(f"{roles_base}/{quote(role_name, safe='')}", headers=headers)
            if gr.status_code == 404:
                cr = await client.post(roles_base, headers=headers, json={"name": role_name})
                cr.raise_for_status()
                gr = await client.get(f"{roles_base}/{quote(role_name, safe='')}", headers=headers)
            gr.raise_for_status()
            role_rep = gr.json()
            if not isinstance(role_rep, dict) or not isinstance(role_rep.get("id"), str):
                raise RuntimeError("Keycloak: ロール表現が不正です")

            ur = await client.get(
                f"{base}/admin/realms/{realm}/users",
                params={"username": grant_username, "exact": "true"},
                headers=headers,
            )
            ur.raise_for_status()
            users = ur.json()
            if not isinstance(users, list) or not users:
                return (
                    f"Keycloak: レルムロール「{role_name}」は用意しましたが、"
                    f"ユーザー名「{grant_username}」が見つからずマッピングをスキップしました。"
                )
            uid = users[0].get("id")
            if not isinstance(uid, str):
                raise RuntimeError("Keycloak: ユーザー id が不正です")

            mr = await client.post(
                f"{base}/admin/realms/{realm}/users/{uid}/role-mappings/realm",
                headers=headers,
                json=[role_rep],
            )
            if mr.status_code not in (200, 204):
                mr.raise_for_status()

            return (
                f"Keycloak: レルムロール「{role_name}」をユーザー「{grant_username}」へ "
                "冪等付与しました。"
            )

    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.text[:500]
        except Exception:
            pass
        logger.warning("Keycloak ロールシード: HTTP エラー %s %s", e.response.status_code, detail)
        return (
            f"Keycloak: ロール自動設定をスキップしました（HTTP {e.response.status_code}）。"
            " 管理コンソールでレルムロールを手動付与するか、KEYCLOAK_SEED_* を確認してください。"
        )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("Keycloak ロールシード: 接続不可 %s", e)
        return (
            "Keycloak: 未起動のためロール自動設定をスキップしました。"
            "（`just deps-up` 後に再実行可能）"
        )
    except Exception as e:
        logger.warning("Keycloak ロールシード: 失敗 %s", e)
        return f"Keycloak: ロール自動設定をスキップしました（{e}）。"
