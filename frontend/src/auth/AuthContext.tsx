import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { initKeycloakClient, keycloak } from "./keycloak";

type AuthContextValue = {
  ready: boolean;
  authenticated: boolean;
  /** Keycloak 初期化失敗時のみ（ブラウザの開発者ツールのコンソールにも出る） */
  initError: string | null;
  getValidToken: () => Promise<string | null>;
  login: () => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    initKeycloakClient()
      .then((auth) => {
        if (cancelled) return;
        setAuthenticated(Boolean(auth));
        setInitError(null);
        setReady(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        console.error("[Keycloak init]", err);
        setAuthenticated(false);
        setInitError(message);
        setReady(true);
      });

    keycloak.onAuthSuccess = () => {
      setInitError(null);
      setAuthenticated(true);
    };
    keycloak.onAuthLogout = () => setAuthenticated(false);
    keycloak.onTokenExpired = () => {
      void keycloak.updateToken(30).catch(() => {
        setAuthenticated(false);
      });
    };

    return () => {
      cancelled = true;
      keycloak.onAuthSuccess = undefined;
      keycloak.onAuthLogout = undefined;
      keycloak.onTokenExpired = undefined;
    };
  }, []);

  const getValidToken = useCallback(async (): Promise<string | null> => {
    if (!keycloak.authenticated) return null;
    try {
      await keycloak.updateToken(30);
      return keycloak.token ?? null;
    } catch {
      return null;
    }
  }, []);

  const login = useCallback(() => {
    void keycloak.login().catch((err: unknown) => {
      console.error("[Keycloak login]", err);
      setInitError(err instanceof Error ? err.message : String(err));
    });
  }, []);

  const logout = useCallback(() => {
    void keycloak.logout({ redirectUri: window.location.origin });
  }, []);

  const value = useMemo(
    () => ({
      ready,
      authenticated,
      initError,
      getValidToken,
      login,
      logout,
    }),
    [ready, authenticated, initError, getValidToken, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth は AuthProvider 内で使ってください");
  }
  return ctx;
}
