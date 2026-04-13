import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { useMemo, useState } from "react";

import {
  createReservation,
  deleteReservation,
  fetchDevices,
  fetchReservations,
} from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

function localInputToIso(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    throw new Error("日時の形式が正しくありません");
  }
  return d.toISOString();
}

export function ReservationsPage() {
  const { authenticated, ready, login, getValidToken } = useAuth();
  const queryClient = useQueryClient();

  const [deviceId, setDeviceId] = useState("");
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [purpose, setPurpose] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

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
    queryKey: ["reservations"],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) return [];
      return fetchReservations(token);
    },
    enabled: authenticated && ready,
  });

  const createMut = useMutation({
    mutationFn: async () => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      if (!deviceId || !startLocal || !endLocal) {
        throw new Error("装置・開始・終了を入力してください");
      }
      return createReservation(token, {
        device_id: deviceId,
        start_time: localInputToIso(startLocal),
        end_time: localInputToIso(endLocal),
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

      <section>
        <h2 className="mb-3 text-lg font-medium">あなたの予約</h2>
        {reservationsQuery.isLoading ? (
          <p className="text-sm text-zinc-600">読み込み中…</p>
        ) : reservationsQuery.isError ? (
          <p className="text-sm text-red-700">予約一覧を取得できませんでした。</p>
        ) : (
          <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white shadow-sm">
            {reservationsQuery.data?.length === 0 ? (
              <li className="p-4 text-sm text-zinc-600">予約はまだありません。</li>
            ) : (
              reservationsQuery.data?.map((r) => (
                <li key={r.id} className="flex flex-wrap items-start justify-between gap-2 p-4">
                  <div className="space-y-1 text-sm">
                    <p className="font-medium">
                      {format(new Date(r.start_time), "PPp", { locale: ja })} 〜{" "}
                      {format(new Date(r.end_time), "PPp", { locale: ja })}
                    </p>
                    <p className="text-xs text-zinc-500">
                      装置: {deviceNameById.get(r.device_id) ?? r.device_id} / {r.status}
                    </p>
                    {r.purpose ? <p className="text-zinc-700">{r.purpose}</p> : null}
                  </div>
                  <button
                    type="button"
                    className="text-sm text-red-700 underline"
                    disabled={deleteMut.isPending}
                    onClick={() => {
                      if (window.confirm("この予約を削除しますか？")) {
                        deleteMut.mutate(r.id);
                      }
                    }}
                  >
                    削除
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
