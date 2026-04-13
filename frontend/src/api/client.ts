import { env } from "../env";

import type {
  Device,
  FacetsResponse,
  PageSize,
  Paginated,
  Reservation,
  UserDirectoryRow,
  UserMe,
} from "./types";

function buildUrl(path: string, params?: Record<string, string | undefined>): string {
  const base = path.startsWith("http") ? path : `${env.apiBase}${path}`;
  if (!params) return base;
  const u = new URL(base, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") u.searchParams.set(k, v);
  }
  return u.pathname + u.search;
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchDevices(filters: {
  q?: string;
  category?: string;
  location?: string;
  status?: string;
  reservation_user?: string;
  reservation_from?: string;
  reservation_to?: string;
  page?: number;
  page_size?: PageSize;
}): Promise<Paginated<Device>> {
  const params: Record<string, string | undefined> = {
    q: filters.q,
    category: filters.category,
    location: filters.location,
    status: filters.status,
    reservation_user: filters.reservation_user,
    reservation_from: filters.reservation_from,
    reservation_to: filters.reservation_to,
    page: filters.page !== undefined ? String(filters.page) : undefined,
    page_size: filters.page_size !== undefined ? String(filters.page_size) : undefined,
  };
  const res = await fetch(buildUrl("/devices", params));
  return parseJson<Paginated<Device>>(res);
}

export async function fetchDevice(deviceId: string): Promise<Device> {
  const res = await fetch(buildUrl(`/devices/${deviceId}`));
  return parseJson<Device>(res);
}

export async function fetchFacets(params: { q?: string }): Promise<FacetsResponse> {
  const res = await fetch(buildUrl("/devices/facets", params));
  return parseJson<FacetsResponse>(res);
}

export async function fetchCurrentUser(token: string): Promise<UserMe> {
  const res = await fetch(buildUrl("/users/me"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<UserMe>(res);
}

export async function fetchUsersAdmin(token: string): Promise<UserDirectoryRow[]> {
  const res = await fetch(buildUrl("/users"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<UserDirectoryRow[]>(res);
}

export async function fetchReservations(token: string): Promise<Reservation[]> {
  const res = await fetch(buildUrl("/reservations"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<Reservation[]>(res);
}

export async function fetchDeviceReservations(
  token: string,
  deviceId: string,
  opts: {
    from: string;
    to: string;
    includeCancelled?: boolean;
    page?: number;
    page_size?: PageSize;
  },
): Promise<Paginated<Reservation>> {
  const res = await fetch(
    buildUrl(`/devices/${deviceId}/reservations`, {
      from: opts.from,
      to: opts.to,
      ...(opts.includeCancelled ? { include_cancelled: "true" } : {}),
      ...(opts.page !== undefined ? { page: String(opts.page) } : {}),
      ...(opts.page_size !== undefined ? { page_size: String(opts.page_size) } : {}),
    }),
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return parseJson<Paginated<Reservation>>(res);
}

/** カレンダー用に窓内の全予約をページングで結合取得する（API の page_size 上限に合わせて複数回取得） */
export async function fetchDeviceReservationsAllInRange(
  token: string,
  deviceId: string,
  opts: { from: string; to: string; includeCancelled?: boolean },
): Promise<Reservation[]> {
  const pageSize: PageSize = 100;
  const merged: Reservation[] = [];
  let page = 1;
  for (;;) {
    const res = await fetchDeviceReservations(token, deviceId, {
      ...opts,
      page,
      page_size: pageSize,
    });
    merged.push(...res.items);
    if (merged.length >= res.total || res.items.length === 0) {
      break;
    }
    page += 1;
    if (page > 500) {
      break;
    }
  }
  return merged;
}

export async function updateReservation(
  token: string,
  reservationId: string,
  body: {
    start_time?: string;
    end_time?: string;
    purpose?: string | null;
    status?: string;
  },
): Promise<Reservation> {
  const res = await fetch(buildUrl(`/reservations/${reservationId}`), {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseJson<Reservation>(res);
}

export async function createReservation(
  token: string,
  body: { device_id: string; start_time: string; end_time: string; purpose?: string },
): Promise<Reservation> {
  const res = await fetch(buildUrl("/reservations"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseJson<Reservation>(res);
}

export async function deleteReservation(token: string, reservationId: string): Promise<void> {
  const res = await fetch(buildUrl(`/reservations/${reservationId}`), {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
}
