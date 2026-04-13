import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function UserPage() {
  const { authenticated, ready, login } = useAuth();
  const meQuery = useCurrentUser();

  if (!ready) {
    return <p className="text-sm text-zinc-600">認証を確認しています…</p>;
  }

  if (!authenticated) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">マイページ</h1>
        <p className="text-sm text-zinc-700">アカウント情報を表示するにはログインが必要です。</p>
        <button
          type="button"
          className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-800"
          onClick={login}
        >
          ログイン
        </button>
      </div>
    );
  }

  if (meQuery.isLoading) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">マイページ</h1>
        <p className="text-sm text-zinc-600">読み込み中…</p>
      </div>
    );
  }

  if (meQuery.isError) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">マイページ</h1>
        <p className="text-sm text-red-700">情報を取得できませんでした: {meQuery.error.message}</p>
        <p className="text-sm text-zinc-600">
          バックエンドが起動しているか、Vite の <code className="font-mono text-xs">/api</code>{" "}
          プロキシを確認してください。
        </p>
      </div>
    );
  }

  const me = meQuery.data;
  if (!me) {
    return null;
  }

  const roleLabel = me.role === "admin" ? "管理者（app-admin 相当）" : "一般ユーザー";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold">マイページ</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Keycloak のトークンとアプリ DB の紐付けに基づく情報です。
        </p>
      </div>

      <section className="max-w-xl rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-[8rem_1fr] sm:gap-x-6 sm:gap-y-3">
          <dt className="font-medium text-zinc-500">表示名</dt>
          <dd className="text-zinc-900">{me.name?.trim() ? me.name : "—"}</dd>

          <dt className="font-medium text-zinc-500">メール</dt>
          <dd className="break-all font-mono text-xs text-zinc-800">{me.email}</dd>

          <dt className="font-medium text-zinc-500">ロール</dt>
          <dd>
            <span className="rounded bg-zinc-100 px-2 py-0.5 font-mono text-xs text-zinc-800">
              {me.role}
            </span>
            <span className="ml-2 text-zinc-600">（{roleLabel}）</span>
          </dd>

          <dt className="font-medium text-zinc-500">Keycloak ID</dt>
          <dd className="break-all font-mono text-xs text-zinc-700">{me.keycloak_id}</dd>

          <dt className="font-medium text-zinc-500">アプリ登録日時</dt>
          <dd className="text-zinc-800">
            {format(new Date(me.created_at), "PPp", { locale: ja })}
          </dd>

          <dt className="font-medium text-zinc-500">内部ユーザー ID</dt>
          <dd className="break-all font-mono text-xs text-zinc-600">{me.id}</dd>
        </dl>
      </section>

      <p className="max-w-xl text-xs leading-relaxed text-zinc-500">
        表示名・メール・パスワードの変更は Keycloak
        のアカウント／管理コンソール側で行ってください。再ログイン後に反映されます。
      </p>

      <div className="flex flex-wrap gap-4 text-sm">
        <Link to="/reservations" className="text-blue-700 underline-offset-2 hover:underline">
          予約一覧へ
        </Link>
        <Link to="/devices" className="text-blue-700 underline-offset-2 hover:underline">
          装置一覧へ
        </Link>
      </div>
    </div>
  );
}
