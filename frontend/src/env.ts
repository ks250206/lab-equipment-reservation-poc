function envString(name: string, fallback: string): string {
  const v = import.meta.env[name];
  return typeof v === "string" && v.length > 0 ? v : fallback;
}

export const env = {
  keycloakUrl: envString("VITE_KEYCLOAK_URL", "http://localhost:8080"),
  keycloakRealm: envString("VITE_KEYCLOAK_REALM", "master"),
  keycloakClientId: envString("VITE_KEYCLOAK_CLIENT_ID", "device-reservation"),
  /** 相対パス推奨（Vite proxy で FastAPI に転送） */
  apiBase: envString("VITE_API_BASE", "/api"),
} as const;
