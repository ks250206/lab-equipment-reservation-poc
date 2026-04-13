import { Link, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function Layout() {
  const { authenticated, login, logout, ready, initError } = useAuth();
  const meQuery = useCurrentUser();

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      {initError ? (
        <div
          className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-950"
          role="alert"
        >
          <strong className="font-semibold">認証の初期化に失敗しました。</strong>
          <span className="ml-1 font-mono text-xs opacity-90">{initError}</span>
          <span className="ml-2 block text-amber-900/90 sm:inline sm:ml-2">
            Keycloak が起動しているか、`frontend/.env` の VITE_KEYCLOAK_* が管理コンソールの設定と一致するか確認してください（ブラウザの開発者ツール → コンソールにも詳細が出ます）。
          </span>
        </div>
      ) : null}
      <header className="flex flex-wrap items-center gap-4 border-b border-zinc-200 bg-white px-4 py-3">
        <Link to="/" className="text-lg font-semibold tracking-tight">
          室内装置予約
        </Link>
        <nav className="flex gap-4 text-sm">
          <Link to="/devices" className="text-blue-700 underline-offset-2 hover:underline">
            装置一覧
          </Link>
          <Link to="/reservations" className="text-blue-700 underline-offset-2 hover:underline">
            予約一覧
          </Link>
          {meQuery.data?.role === "admin" ? (
            <Link to="/admin/users" className="text-blue-700 underline-offset-2 hover:underline">
              ユーザー管理
            </Link>
          ) : null}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {!ready ? (
            <span className="text-sm text-zinc-500">認証を確認しています…</span>
          ) : authenticated ? (
            <button
              type="button"
              className="rounded border border-zinc-300 bg-white px-3 py-1 text-sm hover:bg-zinc-50"
              onClick={logout}
            >
              ログアウト
            </button>
          ) : (
            <button
              type="button"
              className="rounded border border-zinc-300 bg-white px-3 py-1 text-sm hover:bg-zinc-50"
              onClick={login}
            >
              ログイン
            </button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-4">
        <Outlet />
      </main>
    </div>
  );
}
