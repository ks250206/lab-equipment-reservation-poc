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
    initPromise = keycloak.init({
      onLoad: "check-sso",
      pkceMethod: "S256",
    });
  }
  return initPromise;
}

export { keycloak };
