import type { PageSize } from "@/api/types";

export type DeviceListViewMode = "list" | "detail" | "thumbnail";

export type DevicesPageSearchState = {
  q: string;
  category: string;
  location: string;
  status: string;
  used_by_me: boolean;
  favorites_only: boolean;
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
    used_by_me: sp.get("used_by_me") === "1",
    favorites_only: sp.get("favorites_only") === "1",
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
  used_by_me: boolean;
  favorites_only: boolean;
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
  if (args.used_by_me) sp.set("used_by_me", "1");
  if (args.favorites_only) sp.set("favorites_only", "1");
  if (args.page !== 1) sp.set("page", String(args.page));
  if (args.page_size !== 50) sp.set("page_size", String(args.page_size));
  if (args.view !== "thumbnail") sp.set("view", args.view);
  const s = sp.toString();
  return s ? `?${s}` : "";
}
