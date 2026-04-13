const DEVICE_STATUS_CLASS: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-900 ring-1 ring-emerald-200/80",
  maintenance: "bg-amber-100 text-amber-900 ring-1 ring-amber-200/80",
  unavailable: "bg-zinc-200 text-zinc-800 ring-1 ring-zinc-300/80",
  discontinued: "bg-rose-100 text-rose-900 ring-1 ring-rose-200/80",
};

const DEVICE_STATUS_LABEL: Record<string, string> = {
  available: "利用可能",
  maintenance: "メンテナンス",
  unavailable: "利用不可",
  discontinued: "製造終了",
};

const RESERVATION_STATUS_CLASS: Record<string, string> = {
  confirmed: "bg-teal-100 text-teal-900 ring-1 ring-teal-200/80",
  cancelled: "bg-red-100 text-red-900 ring-1 ring-red-200/80",
  completed: "bg-slate-200 text-slate-800 ring-1 ring-slate-300/80",
};

export const RESERVATION_STATUS_LABEL: Record<string, string> = {
  confirmed: "確定",
  cancelled: "キャンセル",
  completed: "完了",
};

function fallbackClass(kind: "device" | "reservation") {
  return kind === "device"
    ? "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-200/80"
    : "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-200/80";
}

export function DeviceStatusTag({ status }: { status: string }) {
  const cls = DEVICE_STATUS_CLASS[status] ?? fallbackClass("device");
  const label = DEVICE_STATUS_LABEL[status] ?? status;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {label}
    </span>
  );
}

export function ReservationStatusTag({ status }: { status: string }) {
  const cls = RESERVATION_STATUS_CLASS[status] ?? fallbackClass("reservation");
  const label = RESERVATION_STATUS_LABEL[status] ?? status;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {label}
    </span>
  );
}
