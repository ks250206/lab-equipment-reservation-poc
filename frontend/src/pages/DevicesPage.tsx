import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { fetchDevices, fetchFacets } from "@/api/client";
import type { Device, PageSize } from "@/api/types";
import { DeviceImageSlot } from "@/components/device/DeviceImageSlot";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import {
  parseDevicesPageSearch,
  serializeDevicesPageSearch,
  type DeviceListViewMode,
} from "@/lib/devicesPageSearch";
import { localDatetimeInputToIso } from "@/lib/datetimeLocal";
import { urlSearchEqual } from "@/lib/urlSearchEqual";

export function DevicesPage() {
  const locationRoute = useLocation();
  const navigate = useNavigate();
  const skipHydrateFromUrl = useRef(false);

  const initial = parseDevicesPageSearch(locationRoute.search);
  const [rawQuery, setRawQuery] = useState(initial.q);
  const [composition, setComposition] = useState(false);
  const [category, setCategory] = useState(initial.category);
  const [location, setLocation] = useState(initial.location);
  const [status, setStatus] = useState(initial.status);
  const [rawReservationUser, setRawReservationUser] = useState(initial.reservation_user);
  const [resUserComposition, setResUserComposition] = useState(false);
  const [reservationFrom, setReservationFrom] = useState(initial.reservation_from);
  const [reservationTo, setReservationTo] = useState(initial.reservation_to);
  const [page, setPage] = useState(initial.page);
  const [pageSize, setPageSize] = useState<PageSize>(initial.page_size);
  const [listView, setListView] = useState<DeviceListViewMode>(initial.view);

  const debouncedQuery = useDebouncedValue(rawQuery, composition);
  const debouncedReservationUser = useDebouncedValue(rawReservationUser, resUserComposition);

  useEffect(() => {
    if (skipHydrateFromUrl.current) {
      skipHydrateFromUrl.current = false;
      return;
    }
    const p = parseDevicesPageSearch(locationRoute.search);
    setCategory(p.category);
    setLocation(p.location);
    setRawQuery(p.q);
    setStatus(p.status);
    setRawReservationUser(p.reservation_user);
    setReservationFrom(p.reservation_from);
    setReservationTo(p.reservation_to);
    setPage(p.page);
    setPageSize(p.page_size);
    setListView(p.view);
  }, [locationRoute.search]);

  useEffect(() => {
    const next = serializeDevicesPageSearch({
      q: debouncedQuery,
      category,
      location,
      status,
      reservation_user: debouncedReservationUser,
      reservation_from: reservationFrom,
      reservation_to: reservationTo,
      page,
      page_size: pageSize,
      view: listView,
    });
    if (urlSearchEqual(next, locationRoute.search)) return;
    skipHydrateFromUrl.current = true;
    navigate({ pathname: locationRoute.pathname, search: next }, { replace: true });
  }, [
    debouncedQuery,
    category,
    location,
    status,
    debouncedReservationUser,
    reservationFrom,
    reservationTo,
    page,
    pageSize,
    listView,
    locationRoute.pathname,
    locationRoute.search,
    navigate,
  ]);

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

  const renderDeviceList = (items: Device[]) => {
    if (listView === "list") {
      return (
        <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white shadow-sm">
          {items.map((d) => (
            <li key={d.id} className="flex flex-wrap items-baseline justify-between gap-2 p-4">
              <div>
                <Link to={`/devices/${d.id}`} className="font-medium text-blue-800 hover:underline">
                  {d.name}
                </Link>
                <p className="text-xs text-zinc-500">
                  {d.category ?? "—"} / {d.location ?? "—"} / {d.status}
                </p>
              </div>
            </li>
          ))}
        </ul>
      );
    }

    if (listView === "detail") {
      return (
        <ul className="space-y-4">
          {items.map((d) => (
            <li
              key={d.id}
              className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm"
            >
              <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-stretch">
                <DeviceImageSlot
                  deviceId={d.id}
                  hasImage={d.has_image ?? false}
                  cacheBust={d.updated_at}
                  className="h-36 w-full shrink-0 sm:h-auto sm:w-44"
                />
                <div className="min-w-0 flex-1 space-y-2 text-sm">
                  <Link
                    to={`/devices/${d.id}`}
                    className="text-lg font-medium text-blue-800 hover:underline"
                  >
                    {d.name}
                  </Link>
                  <p className="text-xs text-zinc-500">
                    {d.category ?? "—"} / {d.location ?? "—"} / {d.status}
                  </p>
                  <p className="line-clamp-4 text-zinc-700">{d.description?.trim() || "—"}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      );
    }

    return (
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {items.map((d) => (
          <li
            key={d.id}
            className="flex flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm"
          >
            <DeviceImageSlot
              deviceId={d.id}
              hasImage={d.has_image ?? false}
              cacheBust={d.updated_at}
              className="aspect-[4/3] w-full"
            />
            <div className="space-y-1 p-3">
              <Link
                to={`/devices/${d.id}`}
                className="line-clamp-2 font-medium text-blue-800 hover:underline"
              >
                {d.name}
              </Link>
              <p className="line-clamp-2 text-xs text-zinc-500">
                {d.category ?? "—"} / {d.location ?? "—"}
              </p>
              <p className="text-xs text-zinc-600">{d.status}</p>
            </div>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold">装置一覧</h1>
        <div className="flex flex-wrap gap-1">
          {(
            [
              ["thumbnail", "サムネ"],
              ["list", "リスト"],
              ["detail", "詳細"],
            ] as const
          ).map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              onClick={() => setListView(mode)}
              className={
                listView === mode
                  ? "rounded border border-zinc-800 bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white"
                  : "rounded border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

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
          {deviceQuery.data?.total === 0 ? (
            <p className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600 shadow-sm">
              該当する装置がありません。
            </p>
          ) : deviceQuery.data?.items ? (
            renderDeviceList(deviceQuery.data.items)
          ) : null}
        </div>
      )}
    </div>
  );
}
