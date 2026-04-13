import { useState } from "react";

import { deviceImageUrl } from "@/lib/deviceImageUrl";

type DeviceImageSlotProps = {
  deviceId: string;
  hasImage: boolean;
  /** 一覧の再取得後にキャッシュを避けるため `updated_at` 等を渡す */
  cacheBust?: string;
  className?: string;
};

/**
 * 装置サムネイル枠。`has_image` が false のとき、または読み込み失敗時は「画像なし」プレースホルダ。
 */
export function DeviceImageSlot({
  deviceId,
  hasImage,
  cacheBust,
  className,
}: DeviceImageSlotProps) {
  const [broken, setBroken] = useState(false);
  const showImg = hasImage && !broken;

  return (
    <div
      className={`relative flex min-h-[5rem] overflow-hidden rounded-lg border border-zinc-200 bg-zinc-100 ${className ?? ""}`}
    >
      {showImg ? (
        <img
          src={deviceImageUrl(deviceId, cacheBust)}
          alt=""
          className="h-full w-full min-h-[5rem] object-cover"
          onError={() => setBroken(true)}
        />
      ) : null}
      {!showImg ? (
        <div className="flex min-h-[5rem] w-full flex-col items-center justify-center gap-1 p-3 text-center text-xs text-zinc-500">
          <span className="text-zinc-400" aria-hidden>
            ▣
          </span>
          <span>画像なし</span>
        </div>
      ) : null}
    </div>
  );
}
