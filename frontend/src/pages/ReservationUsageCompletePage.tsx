import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { completeReservationUsage, fetchDevices, fetchReservations } from "@/api/client";
import type { PageSize } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import { useAppToast } from "@/toast/AppToastProvider";

export function ReservationUsageCompletePage() {
  const toast = useAppToast();
  const { authenticated, ready, login, getValidToken } = useAuth();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSize>(50);
  const [actionError, setActionError] = useState<string | null>(null);

  const devicesQuery = useQuery({
    queryKey: ["devices-for-usage-complete"],
    queryFn: () => fetchDevices({ page: 1, page_size: 100 }),
    enabled: authenticated && ready,
  });

  const deviceNameById = useMemo(() => {
    const m = new Map<string, string>();
    devicesQuery.data?.items.forEach((d) => m.set(d.id, d.name));
    return m;
  }, [devicesQuery.data]);

  const listQuery = useMemo(
    () => ({
      reservation_status: "confirmed" as const,
      page,
      page_size: pageSize,
    }),
    [page, pageSize],
  );

  const reservationsQuery = useQuery({
    queryKey: ["reservations-usage-complete", listQuery],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) throw new Error("ログインが必要です");
      return fetchReservations(token, listQuery);
    },
    enabled: authenticated && ready,
  });

  useEffect(() => {
    if (!reservationsQuery.isSuccess || !reservationsQuery.data) return;
    const totalPages = Math.max(1, Math.ceil(reservationsQuery.data.total / pageSize));
    if (page > totalPages) setPage(totalPages);
  }, [reservationsQuery.isSuccess, reservationsQuery.data, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  const completeMut = useMutation({
    mutationFn: async (id: string) => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      return completeReservationUsage(token, id);
    },
    onSuccess: () => {
      setActionError(null);
      toast("利用完了を報告しました");
      void queryClient.invalidateQueries({ queryKey: ["reservations"] });
      void queryClient.invalidateQueries({ queryKey: ["reservations-usage-complete"] });
      void queryClient.invalidateQueries({ queryKey: ["device-reservations"] });
    },
    onError: (e: Error) => {
      setActionError(e.message);
    },
  });

  if (!ready) {
    return <p className="text-sm text-zinc-600">認証を確認しています…</p>;
  }

  if (!authenticated) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">利用完了報告</h1>
        <p className="text-sm text-zinc-700">報告するにはログインが必要です。</p>
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

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">利用完了報告</h1>
        <p className="text-sm text-zinc-600">
          確定中（confirmed）の予約について、装置の利用が終わったら報告してください。報告後は{" "}
          <strong className="font-medium text-zinc-800">completed</strong>{" "}
          となり、予約一覧からの編集・削除はできなくなります。
        </p>
        <p className="text-sm">
          <Link to="/reservations" className="text-blue-800 underline">
            予約一覧へ戻る
          </Link>
        </p>
      </div>

      {actionError ? (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {actionError}
        </p>
      ) : null}

      {reservationsQuery.isLoading ? (
        <p className="text-sm text-zinc-600">読み込み中…</p>
      ) : reservationsQuery.isError ? (
        <p className="text-sm text-red-700">予約を取得できませんでした。</p>
      ) : (
        <div className="space-y-3">
          <ListPaginationBar
            total={reservationsQuery.data?.total ?? 0}
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
          <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white shadow-sm">
            {reservationsQuery.data?.total === 0 ? (
              <li className="p-4 text-sm text-zinc-600">
                報告対象の確定中予約はありません。{" "}
                <Link to="/devices" className="text-blue-800 underline">
                  装置一覧
                </Link>
                から予約できます。
              </li>
            ) : (
              reservationsQuery.data?.items.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-wrap items-start justify-between gap-3 p-4 text-sm"
                >
                  <div className="min-w-0 space-y-1">
                    <p className="font-medium text-zinc-900">
                      {deviceNameById.get(r.device_id) ?? r.device_id}
                    </p>
                    <p className="text-zinc-600">
                      {format(new Date(r.start_time), "PPp", { locale: ja })} 〜{" "}
                      {format(new Date(r.end_time), "PPp", { locale: ja })}
                    </p>
                    {r.purpose ? <p className="text-zinc-700">{r.purpose}</p> : null}
                  </div>
                  <button
                    type="button"
                    disabled={completeMut.isPending}
                    className="shrink-0 rounded bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
                    onClick={() => {
                      if (
                        !window.confirm(
                          "この予約について利用完了を報告します。よろしいですか？（取り消しできません）",
                        )
                      ) {
                        return;
                      }
                      completeMut.mutate(r.id);
                    }}
                  >
                    利用完了を報告
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
