import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { useEffect, useState } from "react";

import { fetchUsersAdmin, updateUserAdmin } from "@/api/client";
import type { UserSelf } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AdminUsersPage() {
  const { authenticated, ready, login, getValidToken } = useAuth();
  const meQuery = useCurrentUser();
  const queryClient = useQueryClient();

  const [editing, setEditing] = useState<UserSelf | null>(null);
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState<"user" | "admin">("user");
  const [formError, setFormError] = useState<string | null>(null);

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

  useEffect(() => {
    if (editing) {
      setEditName(editing.name ?? "");
      setEditRole(editing.role === "admin" ? "admin" : "user");
      setFormError(null);
    }
  }, [editing]);

  const updateMut = useMutation({
    mutationFn: async () => {
      if (!editing) throw new Error("編集対象がありません");
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      return updateUserAdmin(token, editing.id, {
        name: editName.trim() || null,
        role: editRole,
      });
    },
    onSuccess: () => {
      setFormError(null);
      setEditing(null);
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      void queryClient.invalidateQueries({ queryKey: ["users-me"] });
    },
    onError: (e: Error) => {
      setFormError(e.message);
    },
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
          バックエンドが起動していること、開発時は Vite の <code className="font-mono text-xs">/api</code>{" "}
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
          この画面は<strong className="font-medium">管理者</strong>のみ利用できます。現在のロール:{" "}
          <span className="font-mono text-zinc-800">{meQuery.data.role}</span>
        </p>
        <p className="text-sm text-zinc-600">
          アプリDBの管理者は Keycloak の「realm 管理者」とは別です。初回ログイン前にバックエンドの{" "}
          <code className="rounded bg-zinc-100 px-1 font-mono text-xs">
            KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES
          </code>{" "}
          に Keycloak の <code className="font-mono text-xs">preferred_username</code>（例:{" "}
          <code className="font-mono text-xs">admin</code>）を含めてください。既に一般ユーザーとして登録済みの場合は、DB の{" "}
          <code className="font-mono text-xs">users.role</code> を{" "}
          <code className="font-mono text-xs">admin</code> に更新してから再ログインしてください。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold">ユーザー管理</h1>
        <p className="mt-1 text-sm text-zinc-600">
          アプリ DB の <code className="rounded bg-zinc-100 px-1 font-mono text-xs">users</code>{" "}
          テーブルを表示・更新します（表示名・ロール）。ログインやパスワードの正は Keycloak
          側のままです。この画面は Keycloak 管理コンソールの代替にはなりません。
        </p>
      </div>

      {editing ? (
        <section className="max-w-lg rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-medium">ユーザーを編集</h2>
          <p className="mb-3 font-mono text-xs text-zinc-500">{editing.email}</p>
          <form
            className="grid gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              setFormError(null);
              updateMut.mutate();
            }}
          >
            <label className="block space-y-1">
              <span className="text-sm font-medium text-zinc-700">表示名</span>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                autoComplete="off"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-sm font-medium text-zinc-700">ロール</span>
              <select
                value={editRole}
                onChange={(e) => setEditRole(e.target.value as "user" | "admin")}
                className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </label>
            {formError ? <p className="text-sm text-red-700">{formError}</p> : null}
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={updateMut.isPending}
                className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
              >
                {updateMut.isPending ? "保存中…" : "保存"}
              </button>
              <button
                type="button"
                className="rounded border border-zinc-300 bg-white px-4 py-2 text-sm hover:bg-zinc-50"
                onClick={() => setEditing(null)}
              >
                キャンセル
              </button>
            </div>
          </form>
        </section>
      ) : null}

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
                  <th className="px-4 py-3">メール</th>
                  <th className="px-4 py-3">表示名</th>
                  <th className="px-4 py-3">ロール</th>
                  <th className="px-4 py-3">Keycloak ID</th>
                  <th className="px-4 py-3">登録日</th>
                  <th className="px-4 py-3"> </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {usersQuery.data?.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-50/80">
                    <td className="px-4 py-3 font-medium text-zinc-900">{u.email}</td>
                    <td className="px-4 py-3 text-zinc-700">{u.name ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-zinc-100 px-2 py-0.5 font-mono text-xs text-zinc-800">
                        {u.role}
                      </span>
                    </td>
                    <td className="max-w-[12rem] truncate px-4 py-3 font-mono text-xs text-zinc-500">
                      {u.keycloak_id}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-zinc-600">
                      {format(new Date(u.created_at), "PPp", { locale: ja })}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="text-sm text-blue-700 underline-offset-2 hover:underline"
                        onClick={() => setEditing(u)}
                      >
                        編集
                      </button>
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
