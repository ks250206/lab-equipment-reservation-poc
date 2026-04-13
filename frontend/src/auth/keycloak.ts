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
    // リロード後も Keycloak のブラウザセッションがあればトークンを復元する。
    // `onLoad` なしの init はコールバック URL が無い限りトークンを復元しないため、
    // フルリロードのたびに未ログイン扱いになる。
    // `check-sso` + silent redirect は非表示 iframe で prompt=none を行い、
    // `checkLoginIframe: false` でサードパーティ Cookie に依存するログイン状態 iframe は使わない。
    initPromise = keycloak.init({
      onLoad: "check-sso",
      silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      checkLoginIframe: false,
      pkceMethod: "S256",
      responseMode: "query",
      enableLogging: import.meta.env.DEV,
    });
  }
  return initPromise;
}

export { keycloak };
