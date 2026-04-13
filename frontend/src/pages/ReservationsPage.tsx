import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Pencil } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  createReservation,
  deleteReservation,
  fetchDevices,
  fetchReservations,
} from "@/api/client";
import type { PageSize, Reservation } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { ReservationDetailDialog } from "@/components/device/ReservationDetailDialog";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import { localDatetimeInputToIso } from "@/lib/datetimeLocal";
import {
  parseReservationsPageSearch,
  serializeReservationsPageSearch,
} from "@/lib/reservationsPageSearch";
import { urlSearchEqual } from "@/lib/urlSearchEqual";

const RESERVATION_STATUS_OPTIONS = [
  { value: "", label: "（指定なし）" },
  { value: "confirmed", label: "confirmed" },
  { value: "cancelled", label: "cancelled" },
  { value: "completed", label: "completed" },
] as const;

export function ReservationsPage() {
  const { authenticated, ready, login, getValidToken } = useAuth();
  const queryClient = useQueryClient();
  const locationRoute = useLocation();
  const navigate = useNavigate();
  const skipHydrateFromUrl = useRef(false);

  const initial = parseReservationsPageSearch(locationRoute.search);
  const [filterDeviceId, setFilterDeviceId] = useState(initial.device_id);
  const [filterStatus, setFilterStatus] = useState(initial.reservation_status);
  const [filterFrom, setFilterFrom] = useState(initial.reservation_from);
  const [filterTo, setFilterTo] = useState(initial.reservation_to);
  const [includeCancelled, setIncludeCancelled] = useState(initial.include_cancelled);
  const [page, setPage] = useState(initial.page);
  const [pageSize, setPageSize] = useState<PageSize>(initial.page_size);

  const [deviceId, setDeviceId] = useState("");
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [purpose, setPurpose] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [editReservation, setEditReservation] = useState<Reservation | null>(null);

  useEffect(() => {
    if (!authenticated || !ready) return;
    if (skipHydrateFromUrl.current) {
      skipHydrateFromUrl.current = false;
      return;
    }
    const p = parseReservationsPageSearch(locationRoute.search);
    setFilterDeviceId(p.device_id);
    setFilterStatus(p.reservation_status);
    setFilterFrom(p.reservation_from);
    setFilterTo(p.reservation_to);
    setIncludeCancelled(p.include_cancelled);
    setPage(p.page);
    setPageSize(p.page_size);
  }, [authenticated, ready, locationRoute.search]);

  useEffect(() => {
    if (!authenticated || !ready) return;
    const next = serializeReservationsPageSearch({
      device_id: filterDeviceId,
      reservation_status: filterStatus,
      reservation_from: filterFrom,
      reservation_to: filterTo,
      include_cancelled: includeCancelled,
      page,
      page_size: pageSize,
    });
    if (urlSearchEqual(next, locationRoute.search)) return;
    skipHydrateFromUrl.current = true;
    navigate({ pathname: locationRoute.pathname, search: next }, { replace: true });
  }, [
    filterDeviceId,
    filterStatus,
    filterFrom,
    filterTo,
    includeCancelled,
    page,
    pageSize,
    locationRoute.pathname,
    locationRoute.search,
    navigate,
    authenticated,
    ready,
  ]);

  useEffect(() => {
    setPage(1);
  }, [filterDeviceId, filterStatus, filterFrom, filterTo, includeCancelled]);

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  const listQueryParams = useMemo(() => {
    const a = filterFrom.trim();
    const b = filterTo.trim();
    let fromIso: string | undefined;
    let toIso: string | undefined;
    if (a && b) {
      try {
        fromIso = localDatetimeInputToIso(a);
        toIso = localDatetimeInputToIso(b);
        if (new Date(fromIso).getTime() >= new Date(toIso).getTime()) {
          fromIso = undefined;
          toIso = undefined;
        }
      } catch {
        fromIso = undefined;
        toIso = undefined;
      }
    }
    return {
      device_id: filterDeviceId || undefined,
      reservation_status: filterStatus || undefined,
      from: fromIso,
      to: toIso,
      include_cancelled: includeCancelled,
      page,
      page_size: pageSize,
    };
  }, [filterDeviceId, filterStatus, filterFrom, filterTo, includeCancelled, page, pageSize]);

  const devicesQuery = useQuery({
    queryKey: ["devices-for-reservation"],
    queryFn: () => fetchDevices({ page: 1, page_size: 100 }),
    enabled: authenticated && ready,
  });

  const deviceNameById = useMemo(() => {
    const m = new Map<string, string>();
    devicesQuery.data?.items.forEach((d) => m.set(d.id, d.name));
    return m;
  }, [devicesQuery.data]);

  const reservationsQuery = useQuery({
    queryKey: ["reservations", listQueryParams],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) {
        return { items: [], total: 0, page: 1, page_size: pageSize };
      }
      return fetchReservations(token, listQueryParams);
    },
    enabled: authenticated && ready,
  });

  useEffect(() => {
    if (!reservationsQuery.isSuccess || !reservationsQuery.data) return;
    const totalPages = Math.max(1, Math.ceil(reservationsQuery.data.total / pageSize));
    if (page > totalPages) setPage(totalPages);
  }, [reservationsQuery.isSuccess, reservationsQuery.data, page, pageSize]);

  const createMut = useMutation({
    mutationFn: async () => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      if (!deviceId || !startLocal || !endLocal) {
        throw new Error("装置・開始・終了を入力してください");
      }
      return createReservation(token, {
        device_id: deviceId,
        start_time: localDatetimeInputToIso(startLocal),
        end_time: localDatetimeInputToIso(endLocal),
        purpose: purpose.trim() || undefined,
      });
    },
    onSuccess: () => {
      setFormError(null);
      setPurpose("");
      void queryClient.invalidateQueries({ queryKey: ["reservations"] });
    },
    onError: (e: Error) => {
      setFormError(e.message);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      await deleteReservation(token, id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reservations"] });
    },
  });

  if (!ready) {
    return <p className="text-sm text-zinc-600">認証を確認しています…</p>;
  }

  if (!authenticated) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">予約一覧</h1>
        <p className="text-sm text-zinc-700">予約を表示・作成するにはログインが必要です。</p>
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
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">予約一覧</h1>

      <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-medium">新規予約</h2>
        <form
          className="grid max-w-xl gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setFormError(null);
            createMut.mutate();
          }}
        >
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">装置</span>
            <select
              required
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            >
              <option value="">選択してください</option>
              {devicesQuery.data?.items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">開始</span>
            <input
              type="datetime-local"
              required
              value={startLocal}
              onChange={(e) => setStartLocal(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">終了</span>
            <input
              type="datetime-local"
              required
              value={endLocal}
              onChange={(e) => setEndLocal(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">目的（任意）</span>
            <textarea
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              rows={2}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            />
          </label>
          {formError ? <p className="text-sm text-red-700">{formError}</p> : null}
          <button
            type="submit"
            disabled={createMut.isPending}
            className="w-fit rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {createMut.isPending ? "送信中…" : "予約する"}
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">あなたの予約</h2>

        <div className="grid gap-3 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm md:grid-cols-2">
          <label className="block space-y-1 md:col-span-2">
            <span className="text-sm font-medium text-zinc-700">装置で絞り込み</span>
            <select
              value={filterDeviceId}
              onChange={(e) => setFilterDeviceId(e.target.value)}
              className="w-full max-w-md rounded border border-zinc-300 px-3 py-2 text-sm"
            >
              <option value="">（指定なし）</option>
              {devicesQuery.data?.items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">ステータス</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            >
              {RESERVATION_STATUS_OPTIONS.map((o) => (
                <option key={o.value || "all"} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-end gap-2 pb-0.5">
            <input
              type="checkbox"
              checked={includeCancelled}
              onChange={(e) => setIncludeCancelled(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300"
            />
            <span className="text-sm text-zinc-700">キャンセル済みも含める</span>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">期間・開始（ローカル）</span>
            <input
              type="datetime-local"
              value={filterFrom}
              onChange={(e) => setFilterFrom(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-zinc-700">期間・終了（ローカル）</span>
            <input
              type="datetime-local"
              value={filterTo}
              onChange={(e) => setFilterTo(e.target.value)}
              className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            />
            <span className="text-xs text-zinc-500">
              開始・終了の両方を入れたときだけ API で期間絞り込みします。
            </span>
          </label>
        </div>

        {reservationsQuery.isLoading ? (
          <p className="text-sm text-zinc-600">読み込み中…</p>
        ) : reservationsQuery.isError ? (
          <p className="text-sm text-red-700">予約一覧を取得できませんでした。</p>
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
                <li className="p-4 text-sm text-zinc-600">該当する予約はありません。</li>
              ) : (
                reservationsQuery.data?.items.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-start justify-between gap-2 p-4">
                    <div className="min-w-0 flex-1 space-y-1 text-sm">
                      <p className="font-medium">
                        {format(new Date(r.start_time), "PPp", { locale: ja })} 〜{" "}
                        {format(new Date(r.end_time), "PPp", { locale: ja })}
                      </p>
                      <p className="text-xs text-zinc-500">
                        装置: {deviceNameById.get(r.device_id) ?? r.device_id} / {r.status}
                      </p>
                      {r.purpose ? <p className="text-zinc-700">{r.purpose}</p> : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        className="rounded border border-zinc-300 bg-white p-2 text-zinc-700 hover:bg-zinc-50"
                        aria-label="予約を編集"
                        onClick={() => setEditReservation(r)}
                      >
                        <Pencil className="h-4 w-4" aria-hidden />
                      </button>
                      <button
                        type="button"
                        className={
                          r.status === "completed"
                            ? "cursor-not-allowed rounded border border-zinc-200 bg-zinc-50 px-2 py-1 text-sm text-zinc-400"
                            : "text-sm text-red-700 underline"
                        }
                        disabled={deleteMut.isPending || r.status === "completed"}
                        title={
                          r.status === "completed"
                            ? "完了済みの予約は削除できません"
                            : undefined
                        }
                        onClick={() => {
                          if (r.status === "completed") return;
                          if (window.confirm("この予約を削除しますか？")) {
                            deleteMut.mutate(r.id);
                          }
                        }}
                      >
                        削除
                      </button>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </section>

      <ReservationDetailDialog
        open={editReservation !== null}
        onOpenChange={(open) => {
          if (!open) setEditReservation(null);
        }}
        reservation={editReservation}
        editable
        deviceId={editReservation?.device_id ?? ""}
        getValidToken={getValidToken}
      />
    </div>
  );
}
