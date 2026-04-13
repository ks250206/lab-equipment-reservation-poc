import { Link, Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";

export function Layout() {
  const { authenticated, login, logout, ready } = useAuth();

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
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
