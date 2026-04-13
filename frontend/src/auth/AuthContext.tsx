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
  getValidToken: () => Promise<string | null>;
  login: () => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    initKeycloakClient()
      .then((auth) => {
        if (cancelled) return;
        setAuthenticated(Boolean(auth));
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        setAuthenticated(false);
        setReady(true);
      });

    keycloak.onAuthSuccess = () => setAuthenticated(true);
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
    void keycloak.login();
  }, []);

  const logout = useCallback(() => {
    void keycloak.logout({ redirectUri: window.location.origin });
  }, []);

  const value = useMemo(
    () => ({
      ready,
      authenticated,
      getValidToken,
      login,
      logout,
    }),
    [ready, authenticated, getValidToken, login, logout],
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
