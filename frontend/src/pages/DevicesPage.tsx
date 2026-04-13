import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { fetchDevices, fetchFacets } from "@/api/client";
import type { PageSize } from "@/api/types";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { localDatetimeInputToIso } from "@/lib/datetimeLocal";

export function DevicesPage() {
  const locationRoute = useLocation();
  const [rawQuery, setRawQuery] = useState("");
  const [composition, setComposition] = useState(false);
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState("");
  const [status, setStatus] = useState("");
  const [rawReservationUser, setRawReservationUser] = useState("");
  const [resUserComposition, setResUserComposition] = useState(false);
  const [reservationFrom, setReservationFrom] = useState("");
  const [reservationTo, setReservationTo] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSize>(50);

  const debouncedQuery = useDebouncedValue(rawQuery, composition);
  const debouncedReservationUser = useDebouncedValue(rawReservationUser, resUserComposition);

  useEffect(() => {
    const sp = new URLSearchParams(locationRoute.search);
    setCategory(sp.get("category") ?? "");
    setLocation(sp.get("location") ?? "");
  }, [locationRoute.search]);

  useEffect(() => {
    setPage(1);
  }, [
    debouncedQuery,
    category,
    location,
    status,
    debouncedReservationUser,
    reservationFrom,
    reservationTo,
  ]);

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  const facetQuery = useQuery({
    queryKey: ["device-facets", debouncedQuery],
    queryFn: () => fetchFacets({ q: debouncedQuery || undefined }),
  });

  const reservationPeriodIso = useMemo(() => {
    const a = reservationFrom.trim();
    const b = reservationTo.trim();
    if (!a || !b)
      return { from: undefined as string | undefined, to: undefined as string | undefined };
    try {
      const fromIso = localDatetimeInputToIso(a);
      const toIso = localDatetimeInputToIso(b);
      if (new Date(fromIso).getTime() >= new Date(toIso).getTime()) {
        return { from: undefined, to: undefined };
      }
      return { from: fromIso, to: toIso };
    } catch {
      return { from: undefined, to: undefined };
    }
  }, [reservationFrom, reservationTo]);

  const deviceQuery = useQuery({
    queryKey: [
      "devices",
      debouncedQuery,
      category,
      location,
      status,
      debouncedReservationUser,
      reservationPeriodIso.from,
      reservationPeriodIso.to,
      page,
      pageSize,
    ],
    queryFn: () =>
      fetchDevices({
        q: debouncedQuery || undefined,
        category: category || undefined,
        location: location || undefined,
        status: status || undefined,
        reservation_user: debouncedReservationUser.trim() || undefined,
        reservation_from: reservationPeriodIso.from,
        reservation_to: reservationPeriodIso.to,
        page,
        page_size: pageSize,
      }),
  });

  useEffect(() => {
    if (!deviceQuery.isSuccess || !deviceQuery.data) return;
    const totalPages = Math.max(1, Math.ceil(deviceQuery.data.total / pageSize));
    if (page > totalPages) setPage(totalPages);
  }, [deviceQuery.isSuccess, deviceQuery.data, page, pageSize]);

  const categoryOptions = useMemo(
    () => facetQuery.data?.category ?? [],
    [facetQuery.data?.category],
  );
  const locationOptions = useMemo(
    () => facetQuery.data?.location ?? [],
    [facetQuery.data?.location],
  );
  const statusOptions = useMemo(() => facetQuery.data?.status ?? [], [facetQuery.data?.status]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">装置一覧</h1>

      <div className="grid gap-4 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm md:grid-cols-2">
        <label className="block space-y-1 md:col-span-2">
          <span className="text-sm font-medium text-zinc-700">キーワード</span>
          <input
            type="search"
            value={rawQuery}
            onChange={(e) => setRawQuery(e.target.value)}
            onCompositionStart={() => setComposition(true)}
            onCompositionEnd={() => setComposition(false)}
            placeholder="名称・説明・場所・カテゴリで検索"
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            autoComplete="off"
          />
          <span className="text-xs text-zinc-500">
            入力確定から 300ms 後に検索します（IME 変換中は待ちます）
          </span>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-zinc-700">カテゴリ</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
          >
            <option value="">（指定なし）</option>
            {categoryOptions.map((c) => (
              <option key={c.value} value={c.value}>
                {c.value} ({c.count})
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-zinc-700">設置場所</span>
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
          >
            <option value="">（指定なし）</option>
            {locationOptions.map((c) => (
              <option key={c.value} value={c.value}>
                {c.value} ({c.count})
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1 md:col-span-2">
          <span className="text-sm font-medium text-zinc-700">ステータス</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full max-w-xs rounded border border-zinc-300 px-3 py-2 text-sm"
          >
            <option value="">（指定なし）</option>
            {statusOptions.map((c) => (
              <option key={c.value} value={c.value}>
                {c.value} ({c.count})
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1 md:col-span-2">
          <span className="text-sm font-medium text-zinc-700">
            予約ユーザー（氏名・メールの一部）
          </span>
          <input
            type="search"
            value={rawReservationUser}
            onChange={(e) => setRawReservationUser(e.target.value)}
            onCompositionStart={() => setResUserComposition(true)}
            onCompositionEnd={() => setResUserComposition(false)}
            placeholder="例: 山田 または メールの一部"
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
            autoComplete="off"
          />
          <span className="text-xs text-zinc-500">
            入力確定から 300ms 後に反映します（IME 変換中は待ちます）
          </span>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-zinc-700">予約が重なる期間・開始</span>
          <input
            type="datetime-local"
            value={reservationFrom}
            onChange={(e) => setReservationFrom(e.target.value)}
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-zinc-700">予約が重なる期間・終了</span>
          <input
            type="datetime-local"
            value={reservationTo}
            onChange={(e) => setReservationTo(e.target.value)}
            className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
          />
          <span className="text-xs text-zinc-500">
            開始・終了の両方を入れたときだけ期間で絞り込みます。
          </span>
        </label>
      </div>

      {deviceQuery.isLoading ? (
        <p className="text-sm text-zinc-600">読み込み中…</p>
      ) : deviceQuery.isError ? (
        <p className="text-sm text-red-700">
          装置一覧を取得できませんでした。バックエンドとプロキシ設定を確認してください。
        </p>
      ) : (
        <div className="space-y-3">
          {deviceQuery.isSuccess && deviceQuery.data ? (
            <ListPaginationBar
              total={deviceQuery.data.total}
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          ) : null}
          <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white shadow-sm">
            {deviceQuery.data?.total === 0 ? (
              <li className="p-4 text-sm text-zinc-600">該当する装置がありません。</li>
            ) : (
              deviceQuery.data?.items.map((d) => (
                <li key={d.id} className="flex flex-wrap items-baseline justify-between gap-2 p-4">
                  <div>
                    <Link
                      to={`/devices/${d.id}`}
                      className="font-medium text-blue-800 hover:underline"
                    >
                      {d.name}
                    </Link>
                    <p className="text-xs text-zinc-500">
                      {d.category ?? "—"} / {d.location ?? "—"} / {d.status}
                    </p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
