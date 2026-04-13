import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Link, useParams } from "react-router-dom";

import { fetchDevice, uploadDeviceImage } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { DeviceImageSlot } from "@/components/device/DeviceImageSlot";
import { DeviceReservationsSection } from "@/components/device/DeviceReservationsSection";
import { useCurrentUser } from "@/hooks/useCurrentUser";

function devicesListLink(search: Record<string, string>) {
  const q = new URLSearchParams(search).toString();
  return q ? `/devices?${q}` : "/devices";
}

export function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const queryClient = useQueryClient();
  const { authenticated, ready, getValidToken } = useAuth();
  const meQuery = useCurrentUser();
  const isAdmin = meQuery.data?.role === "admin";

  const q = useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId!),
    enabled: Boolean(deviceId),
  });

  const uploadMut = useMutation({
    mutationFn: async (file: File) => {
      const token = await getValidToken();
      if (!token) throw new Error("ログインが必要です");
      if (!deviceId) throw new Error("装置 ID がありません");
      return uploadDeviceImage(token, deviceId, file);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
  });

  if (!deviceId) {
    return <p className="text-sm text-red-700">装置 ID が不正です。</p>;
  }

  if (q.isLoading) {
    return <p className="text-sm text-zinc-600">読み込み中…</p>;
  }

  if (q.isError || !q.data) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-red-700">装置を取得できませんでした。</p>
        <Link to="/devices" className="text-sm text-blue-800 underline">
          一覧に戻る
        </Link>
      </div>
    );
  }

  const d = q.data;
  const hasImage = d.has_image ?? false;

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <nav aria-label="パンくずリスト" className="text-sm text-zinc-600">
          <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            <li>
              <Link to="/devices" className="text-blue-800 underline hover:text-blue-900">
                装置一覧
              </Link>
            </li>
            <li className="text-zinc-400" aria-hidden="true">
              &gt;
            </li>
            <li>
              {d.location ? (
                <Link
                  to={devicesListLink({ location: d.location })}
                  className="text-blue-800 underline hover:text-blue-900"
                >
                  {d.location}
                </Link>
              ) : (
                <span className="text-zinc-500">—</span>
              )}
            </li>
            <li className="text-zinc-400" aria-hidden="true">
              &gt;
            </li>
            <li className="font-medium text-zinc-800" aria-current="page">
              {d.name}
            </li>
          </ol>
        </nav>
        <h1 className="text-2xl font-semibold">{d.name}</h1>
      </div>

      <div className="flex flex-col gap-6 md:flex-row md:items-start md:gap-8">
        <dl className="grid min-w-0 flex-1 gap-2 text-sm sm:max-w-xl md:grid-cols-3">
          <dt className="font-medium text-zinc-600">ステータス</dt>
          <dd className="md:col-span-2">{d.status}</dd>
          <dt className="font-medium text-zinc-600">カテゴリ</dt>
          <dd className="md:col-span-2">
            {d.category ? (
              <Link
                to={devicesListLink({ category: d.category })}
                className="text-blue-800 underline hover:text-blue-900"
              >
                {d.category}
              </Link>
            ) : (
              "—"
            )}
          </dd>
          <dt className="font-medium text-zinc-600">設置場所</dt>
          <dd className="md:col-span-2">
            {d.location ? (
              <Link
                to={devicesListLink({ location: d.location })}
                className="text-blue-800 underline hover:text-blue-900"
              >
                {d.location}
              </Link>
            ) : (
              "—"
            )}
          </dd>
          <dt className="font-medium text-zinc-600">説明</dt>
          <dd className="md:col-span-2 whitespace-pre-wrap">{d.description ?? "—"}</dd>
          <dt className="font-medium text-zinc-600">更新</dt>
          <dd className="md:col-span-2">
            {format(new Date(d.updated_at), "PPpp", { locale: ja })}
          </dd>
        </dl>

        <aside className="w-full shrink-0 space-y-3 md:sticky md:top-4 md:w-72">
          <h2 className="text-sm font-medium text-zinc-700">装置写真</h2>
          <DeviceImageSlot
            deviceId={deviceId}
            hasImage={hasImage}
            cacheBust={d.updated_at}
            className="aspect-square w-full max-w-sm md:max-w-none"
          />
          {isAdmin && authenticated && ready ? (
            <div className="space-y-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-sm">
              <label className="block space-y-1">
                <span className="font-medium text-zinc-700">
                  画像を更新（PNG / JPEG、最大 2MB）
                </span>
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  disabled={uploadMut.isPending}
                  className="w-full text-xs file:mr-2 file:rounded file:border file:border-zinc-300 file:bg-white file:px-2 file:py-1"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = "";
                    if (f) uploadMut.mutate(f);
                  }}
                />
              </label>
              {uploadMut.isError ? (
                <p className="text-xs text-red-700">
                  {uploadMut.error instanceof Error
                    ? uploadMut.error.message
                    : "アップロードに失敗しました"}
                </p>
              ) : null}
              {uploadMut.isPending ? (
                <p className="text-xs text-zinc-600">アップロード中…</p>
              ) : null}
            </div>
          ) : null}
        </aside>
      </div>

      <DeviceReservationsSection deviceId={deviceId} />
    </div>
  );
}
