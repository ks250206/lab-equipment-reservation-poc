import { env } from "@/env";

/** 装置画像 GET（認証不要）。キャッシュ破棄に `updated_at` を付与できる。 */
export function deviceImageUrl(deviceId: string, cacheBust?: string): string {
  const q = cacheBust ? `?t=${encodeURIComponent(cacheBust)}` : "";
  return `${env.apiBase}/devices/${deviceId}/image${q}`;
}
