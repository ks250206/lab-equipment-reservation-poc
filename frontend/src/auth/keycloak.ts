import Keycloak from "keycloak-js";

import { env } from "../env";

const keycloak = new Keycloak({
  url: env.keycloakUrl,
  realm: env.keycloakRealm,
  clientId: env.keycloakClientId,
});

let initPromise: Promise<boolean> | null = null;

/** 同一インスタンスで init を複数回呼ばない */
export function initKeycloakClient(): Promise<boolean> {
  if (!initPromise) {
    // onLoad: "check-sso" はサードパーティ Cookie 制限で iframe が無効化されると、
    // prompt=none のリダイレクトだけが走り未ログイン時に失敗しやすい（ログインボタン以前に詰まる）。
    // 明示ログインは keycloak.login() に任せ、コールバックは初回 init の URL 解析で処理する。
    initPromise = keycloak.init({
      pkceMethod: "S256",
      responseMode: "query",
      enableLogging: import.meta.env.DEV,
    });
  }
  return initPromise;
}

export { keycloak };
