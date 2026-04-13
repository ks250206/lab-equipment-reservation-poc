import type { PageSize } from "@/api/types";

export type ReservationsPageSearchState = {
  device_id: string;
  reservation_status: string;
  reservation_from: string;
  reservation_to: string;
  include_cancelled: boolean;
  page: number;
  page_size: PageSize;
};

const PAGE_SIZES: PageSize[] = [20, 50, 100];

export function parseReservationsPageSearch(search: string): ReservationsPageSearchState {
  const sp = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const pageRaw = parseInt(sp.get("page") ?? "1", 10);
  const page = Number.isFinite(pageRaw) && pageRaw >= 1 ? pageRaw : 1;
  const psRaw = parseInt(sp.get("page_size") ?? "50", 10);
  const page_size = PAGE_SIZES.includes(psRaw as PageSize) ? (psRaw as PageSize) : 50;
  const ic = sp.get("include_cancelled");
  const include_cancelled = ic === "1" || ic === "true";

  return {
    device_id: sp.get("device_id") ?? "",
    reservation_status: sp.get("reservation_status") ?? "",
    reservation_from: sp.get("reservation_from") ?? "",
    reservation_to: sp.get("reservation_to") ?? "",
    include_cancelled,
    page,
    page_size,
  };
}

export function serializeReservationsPageSearch(args: ReservationsPageSearchState): string {
  const sp = new URLSearchParams();
  if (args.device_id) sp.set("device_id", args.device_id);
  if (args.reservation_status) sp.set("reservation_status", args.reservation_status);
  if (args.reservation_from.trim()) sp.set("reservation_from", args.reservation_from.trim());
  if (args.reservation_to.trim()) sp.set("reservation_to", args.reservation_to.trim());
  if (args.include_cancelled) sp.set("include_cancelled", "1");
  if (args.page !== 1) sp.set("page", String(args.page));
  if (args.page_size !== 50) sp.set("page_size", String(args.page_size));
  const s = sp.toString();
  return s ? `?${s}` : "";
}
