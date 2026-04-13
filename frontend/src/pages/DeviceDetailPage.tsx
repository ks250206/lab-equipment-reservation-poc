import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { Link, useParams } from "react-router-dom";

import { fetchDevice } from "@/api/client";
import { DeviceReservationsSection } from "@/components/device/DeviceReservationsSection";

export function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  const q = useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId!),
    enabled: Boolean(deviceId),
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

  return (
    <div className="space-y-4">
      <div className="text-sm">
        <Link to="/devices" className="text-blue-800 underline">
          ← 装置一覧
        </Link>
      </div>
      <h1 className="text-2xl font-semibold">{d.name}</h1>
      <dl className="grid max-w-xl gap-2 text-sm md:grid-cols-3">
        <dt className="font-medium text-zinc-600">ステータス</dt>
        <dd className="md:col-span-2">{d.status}</dd>
        <dt className="font-medium text-zinc-600">カテゴリ</dt>
        <dd className="md:col-span-2">{d.category ?? "—"}</dd>
        <dt className="font-medium text-zinc-600">設置場所</dt>
        <dd className="md:col-span-2">{d.location ?? "—"}</dd>
        <dt className="font-medium text-zinc-600">説明</dt>
        <dd className="md:col-span-2 whitespace-pre-wrap">{d.description ?? "—"}</dd>
        <dt className="font-medium text-zinc-600">更新</dt>
        <dd className="md:col-span-2">{format(new Date(d.updated_at), "PPpp", { locale: ja })}</dd>
      </dl>
      <DeviceReservationsSection deviceId={deviceId} />
    </div>
  );
}
