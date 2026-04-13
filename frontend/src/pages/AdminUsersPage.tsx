import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

import { fetchUsersAdmin } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AdminUsersPage() {
  const { authenticated, ready, login, getValidToken } = useAuth();
  const meQuery = useCurrentUser();

  const isAdmin = meQuery.data?.role === "admin";

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      return fetchUsersAdmin(token);
    },
    enabled: Boolean(authenticated && ready && isAdmin),
  });

  if (!ready || meQuery.isLoading) {
    return <p className="text-sm text-zinc-600">認証を確認しています…</p>;
  }

  if (!authenticated) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="text-sm text-zinc-700">この画面を表示するにはログインが必要です。</p>
        <button
          type="button"
          className="rounded border border-zinc-300 bg-white px-4 py-2 text-sm hover:bg-zinc-50"
          onClick={login}
        >
          ログイン
        </button>
      </div>
    );
  }

  if (meQuery.isError) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="text-sm text-red-700">
          ユーザー情報を取得できませんでした: {meQuery.error.message}
        </p>
        <p className="text-sm text-zinc-600">
          バックエンドが起動していること、開発時は Vite の{" "}
          <code className="font-mono text-xs">/api</code>{" "}
          プロキシ経由でアクセスしていることを確認してください。
        </p>
      </div>
    );
  }

  if (!meQuery.data) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="text-sm text-zinc-600">ユーザー情報を読み込み中です…</p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="text-sm text-zinc-700">
          この画面は<strong className="font-medium">管理者</strong>
          のみ利用できます。トークン上のロール:{" "}
          <span className="font-mono text-zinc-800">{meQuery.data.role}</span>
        </p>
        <p className="text-sm text-zinc-600">
          管理者は Keycloak のレルムロール <code className="font-mono text-xs">app-admin</code>{" "}
          がアクセストークンに含まれている必要があります。開発では{" "}
          <code className="font-mono text-xs">just seed-dev</code> が Keycloak 管理 API
          で付与を試みます。手動の場合は{" "}
          <code className="font-mono text-xs">doc/keycloak-setup.md</code> を参照してください。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="mt-1 text-sm text-zinc-600">
          アプリ DB の <code className="rounded bg-zinc-100 px-1 font-mono text-xs">users</code> は{" "}
          <strong className="font-medium">内部 ID</strong> と Keycloak 主体（
          <code className="font-mono text-xs">sub</code>
          ）の対応のみを保持します。メール・表示名・レルムロールの正は Keycloak および
          JWT。一覧のメール列はありません（Keycloak 管理コンソールで照合してください）。
        </p>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-medium">ユーザー一覧</h2>
        {usersQuery.isLoading ? (
          <p className="text-sm text-zinc-600">読み込み中…</p>
        ) : usersQuery.isError ? (
          <p className="text-sm text-red-700">
            一覧を取得できませんでした（管理者でログインしているか確認してください）。
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-zinc-200 bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-600">
                <tr>
                  <th className="px-4 py-3">内部 ID</th>
                  <th className="px-4 py-3">Keycloak ID（sub）</th>
                  <th className="px-4 py-3">登録日</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {usersQuery.data?.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-50/80">
                    <td className="px-4 py-3 font-mono text-xs text-zinc-700">{u.id}</td>
                    <td className="max-w-[20rem] truncate px-4 py-3 font-mono text-xs text-zinc-600">
                      {u.keycloak_id}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-zinc-600">
                      {format(new Date(u.created_at), "PPp", { locale: ja })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
