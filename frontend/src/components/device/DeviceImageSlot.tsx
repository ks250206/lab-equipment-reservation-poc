import { useState } from "react";
import { Link } from "react-router-dom";

import { deviceImageUrl } from "@/lib/deviceImageUrl";

type DeviceImageSlotProps = {
  deviceId: string;
  hasImage: boolean;
  /** 一覧の再取得後にキャッシュを避けるため `updated_at` 等を渡す */
  cacheBust?: string;
  className?: string;
  /** 指定時はクリックで装置詳細へ遷移（サムネ・一覧の画像枠用） */
  to?: string;
};

/**
 * 装置サムネイル枠。`has_image` が false のとき、または読み込み失敗時は「画像なし」プレースホルダ。
 */
export function DeviceImageSlot({
  deviceId,
  hasImage,
  cacheBust,
  className,
  to,
}: DeviceImageSlotProps) {
  const [broken, setBroken] = useState(false);
  const showImg = hasImage && !broken;

  const shellClass = `relative flex min-h-[5rem] overflow-hidden rounded-lg border border-zinc-200 bg-zinc-100 ${className ?? ""}`;

  const body = (
    <>
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
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        className={`${shellClass} block ring-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500`}
        aria-label="装置の詳細を表示"
      >
        {body}
      </Link>
    );
  }

  return <div className={shellClass}>{body}</div>;
}
