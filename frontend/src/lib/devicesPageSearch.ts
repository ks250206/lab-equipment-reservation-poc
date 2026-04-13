import type { PageSize } from "@/api/types";

export type DeviceListViewMode = "list" | "detail" | "thumbnail";

export type DevicesPageSearchState = {
  q: string;
  category: string;
  location: string;
  status: string;
  reservation_user: string;
  reservation_from: string;
  reservation_to: string;
  page: number;
  page_size: PageSize;
  view: DeviceListViewMode;
};

const PAGE_SIZES: PageSize[] = [20, 50, 100];
const VIEWS: DeviceListViewMode[] = ["list", "detail", "thumbnail"];

export function parseDevicesPageSearch(search: string): DevicesPageSearchState {
  const sp = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const pageRaw = parseInt(sp.get("page") ?? "1", 10);
  const page = Number.isFinite(pageRaw) && pageRaw >= 1 ? pageRaw : 1;
  const psRaw = parseInt(sp.get("page_size") ?? "50", 10);
  const page_size = PAGE_SIZES.includes(psRaw as PageSize) ? (psRaw as PageSize) : 50;
  const viewRaw = sp.get("view") ?? "";
  const view = VIEWS.includes(viewRaw as DeviceListViewMode)
    ? (viewRaw as DeviceListViewMode)
    : "thumbnail";

  return {
    q: sp.get("q") ?? "",
    category: sp.get("category") ?? "",
    location: sp.get("location") ?? "",
    status: sp.get("status") ?? "",
    reservation_user: sp.get("reservation_user") ?? "",
    reservation_from: sp.get("reservation_from") ?? "",
    reservation_to: sp.get("reservation_to") ?? "",
    page,
    page_size,
    view,
  };
}

export function serializeDevicesPageSearch(args: {
  q: string;
  category: string;
  location: string;
  status: string;
  reservation_user: string;
  reservation_from: string;
  reservation_to: string;
  page: number;
  page_size: PageSize;
  view: DeviceListViewMode;
}): string {
  const sp = new URLSearchParams();
  const q = args.q.trim();
  if (q) sp.set("q", q);
  if (args.category) sp.set("category", args.category);
  if (args.location) sp.set("location", args.location);
  if (args.status) sp.set("status", args.status);
  const ru = args.reservation_user.trim();
  if (ru) sp.set("reservation_user", ru);
  if (args.reservation_from.trim()) sp.set("reservation_from", args.reservation_from.trim());
  if (args.reservation_to.trim()) sp.set("reservation_to", args.reservation_to.trim());
  if (args.page !== 1) sp.set("page", String(args.page));
  if (args.page_size !== 50) sp.set("page_size", String(args.page_size));
  if (args.view !== "thumbnail") sp.set("view", args.view);
  const s = sp.toString();
  return s ? `?${s}` : "";
}
