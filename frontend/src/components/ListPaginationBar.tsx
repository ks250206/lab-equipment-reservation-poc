import { useEffect, useState } from "react";

import type { PageSize } from "@/api/types";

type ListPaginationBarProps = {
  total: number;
  page: number;
  pageSize: PageSize;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: PageSize) => void;
};

const btnClass =
  "rounded border border-zinc-300 bg-white px-2.5 py-1 text-xs hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40";

export function ListPaginationBar({
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: ListPaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);
  const [jump, setJump] = useState(String(safePage));

  useEffect(() => {
    setJump(String(safePage));
  }, [safePage]);

  const from = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const to = Math.min(total, safePage * pageSize);

  const applyJump = () => {
    const n = Number.parseInt(jump, 10);
    if (!Number.isFinite(n)) return;
    onPageChange(Math.min(Math.max(1, n), totalPages));
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-zinc-50/80 p-3 text-sm sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <p className="text-zinc-600">
        全 {total} 件中 {from}–{to} 件を表示（{safePage} / {totalPages} ページ）
      </p>
      <label className="flex items-center gap-2">
        <span className="text-zinc-600">表示件数</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value) as PageSize)}
          className="rounded border border-zinc-300 bg-white px-2 py-1 text-xs"
        >
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </label>
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          className={btnClass}
          disabled={safePage <= 1}
          onClick={() => onPageChange(1)}
        >
          最初
        </button>
        <button
          type="button"
          className={btnClass}
          disabled={safePage <= 1}
          onClick={() => onPageChange(safePage - 1)}
        >
          前へ
        </button>
        <button
          type="button"
          className={btnClass}
          disabled={safePage >= totalPages}
          onClick={() => onPageChange(safePage + 1)}
        >
          次へ
        </button>
        <button
          type="button"
          className={btnClass}
          disabled={safePage >= totalPages}
          onClick={() => onPageChange(totalPages)}
        >
          最後
        </button>
        <span className="mx-1 text-zinc-400">|</span>
        <label className="flex items-center gap-1.5 text-xs text-zinc-600">
          ページ
          <input
            type="text"
            inputMode="numeric"
            value={jump}
            onChange={(e) => setJump(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") applyJump();
            }}
            className="w-14 rounded border border-zinc-300 bg-white px-2 py-1 text-center"
            aria-label="移動先ページ番号"
          />
          <button type="button" className={btnClass} onClick={applyJump}>
            移動
          </button>
        </label>
      </div>
    </div>
  );
}
