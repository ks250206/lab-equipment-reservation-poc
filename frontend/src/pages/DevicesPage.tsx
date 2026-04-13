import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { fetchDevices, fetchFacets } from "@/api/client";
import type { Device, PageSize } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { DeviceImageSlot } from "@/components/device/DeviceImageSlot";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import { DeviceStatusTag } from "@/components/StatusTags";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import {
  parseDevicesPageSearch,
  serializeDevicesPageSearch,
  type DeviceListViewMode,
} from "@/lib/devicesPageSearch";
import { urlSearchEqual } from "@/lib/urlSearchEqual";

export function DevicesPage() {
  const locationRoute = useLocation();
  const navigate = useNavigate();
  const skipHydrateFromUrl = useRef(false);
  const { authenticated, ready, getValidToken } = useAuth();

  const initial = parseDevicesPageSearch(locationRoute.search);
  const [rawQuery, setRawQuery] = useState(initial.q);
  const [composition, setComposition] = useState(false);
  const [category, setCategory] = useState(initial.category);
  const [location, setLocation] = useState(initial.location);
  const [status, setStatus] = useState(initial.status);
  const [usedByMe, setUsedByMe] = useState(initial.used_by_me);
  const [favoritesOnly, setFavoritesOnly] = useState(initial.favorites_only);
  const [page, setPage] = useState(initial.page);
  const [pageSize, setPageSize] = useState<PageSize>(initial.page_size);
  const [listView, setListView] = useState<DeviceListViewMode>(initial.view);

  const debouncedQuery = useDebouncedValue(rawQuery, composition);

  useEffect(() => {
    if (!ready || authenticated) return;
    if (usedByMe) setUsedByMe(false);
    if (favoritesOnly) setFavoritesOnly(false);
  }, [ready, authenticated, usedByMe, favoritesOnly]);

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
    setUsedByMe(p.used_by_me);
    setFavoritesOnly(p.favorites_only);
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
      used_by_me: usedByMe,
      favorites_only: favoritesOnly,
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
    usedByMe,
    favoritesOnly,
    page,
    pageSize,
    listView,
    locationRoute.pathname,
    locationRoute.search,
    navigate,
  ]);

  useEffect(() => {
    setPage(1);
  }, [debouncedQuery, category, location, status, usedByMe, favoritesOnly]);

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  const facetQuery = useQuery({
    queryKey: ["device-facets", debouncedQuery],
    queryFn: () => fetchFacets({ q: debouncedQuery || undefined }),
  });

  const deviceQuery = useQuery({
    queryKey: [
      "devices",
      debouncedQuery,
      category,
      location,
      status,
      usedByMe,
      favoritesOnly,
      page,
      pageSize,
      authenticated,
    ],
    queryFn: async () => {
      const token = authenticated && ready ? await getValidToken().catch(() => null) : null;
      return fetchDevices(
        {
          q: debouncedQuery || undefined,
          category: category || undefined,
          location: location || undefined,
          status: status || undefined,
          used_by_me: usedByMe,
          favorites_only: favoritesOnly,
          page,
          page_size: pageSize,
        },
        { accessToken: token },
      );
    },
    enabled: ready,
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

  const personalFiltersDisabled = !authenticated;

  const renderDeviceList = (items: Device[]) => {
    if (listView === "list") {
      return (
        <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white shadow-sm">
          {items.map((d) => (
            <li key={d.id} className="flex flex-wrap items-baseline justify-between gap-2 p-4">
              <div className="flex min-w-0 items-baseline gap-2">
                {d.is_favorite ? (
                  <Star
                    className="h-4 w-4 shrink-0 fill-amber-400 text-amber-500"
                    aria-label="お気に入り"
                  />
                ) : null}
                <div className="min-w-0">
                  <Link
                    to={`/devices/${d.id}`}
                    className="font-medium text-blue-800 hover:underline"
                  >
                    {d.name}
                  </Link>
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                    <span>
                      {d.category ?? "—"} / {d.location ?? "—"}
                    </span>
                    <DeviceStatusTag status={d.status} />
                  </p>
                </div>
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
                  to={`/devices/${d.id}`}
                />
                <div className="min-w-0 flex-1 space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    {d.is_favorite ? (
                      <Star
                        className="mt-1 h-5 w-5 shrink-0 fill-amber-400 text-amber-500"
                        aria-label="お気に入り"
                      />
                    ) : null}
                    <Link
                      to={`/devices/${d.id}`}
                      className="text-lg font-medium text-blue-800 hover:underline"
                    >
                      {d.name}
                    </Link>
                  </div>
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                    <span>
                      {d.category ?? "—"} / {d.location ?? "—"}
                    </span>
                    <DeviceStatusTag status={d.status} />
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
              to={`/devices/${d.id}`}
            />
            <div className="space-y-1 p-3">
              <div className="flex items-start gap-1.5">
                {d.is_favorite ? (
                  <Star
                    className="mt-0.5 h-4 w-4 shrink-0 fill-amber-400 text-amber-500"
                    aria-label="お気に入り"
                  />
                ) : null}
                <Link
                  to={`/devices/${d.id}`}
                  className="line-clamp-2 font-medium text-blue-800 hover:underline"
                >
                  {d.name}
                </Link>
              </div>
              <p className="line-clamp-2 text-xs text-zinc-500">
                {d.category ?? "—"} / {d.location ?? "—"}
              </p>
              <div className="pt-0.5">
                <DeviceStatusTag status={d.status} />
              </div>
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

        <div className="flex flex-col gap-2 md:col-span-2">
          <span className="text-sm font-medium text-zinc-700">マイ向け（ログイン時のみ）</span>
          <div className="flex flex-wrap gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-zinc-800">
              <input
                type="checkbox"
                checked={usedByMe}
                disabled={personalFiltersDisabled}
                onChange={(e) => setUsedByMe(e.target.checked)}
                className="rounded border-zinc-300"
              />
              使ったことがある装置のみ
            </label>
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-zinc-800">
              <input
                type="checkbox"
                checked={favoritesOnly}
                disabled={personalFiltersDisabled}
                onChange={(e) => setFavoritesOnly(e.target.checked)}
                className="rounded border-zinc-300"
              />
              お気に入りのみ
            </label>
          </div>
          {personalFiltersDisabled ? (
            <p className="text-xs text-zinc-500">ログインすると利用できます。</p>
          ) : null}
        </div>
      </div>

      {deviceQuery.isLoading ? (
        <p className="text-sm text-zinc-600">読み込み中…</p>
      ) : deviceQuery.isError ? (
        <p className="text-sm text-red-700">
          装置一覧を取得できませんでした。
          {deviceQuery.error instanceof Error ? `（${deviceQuery.error.message}）` : null}
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
