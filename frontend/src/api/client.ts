import { env } from "../env";

import type { Device, FacetsResponse, Reservation, UserSelf } from "./types";

export type UserUpdateBody = { name?: string | null; role?: string };

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
}): Promise<Device[]> {
  const res = await fetch(buildUrl("/devices", filters));
  return parseJson<Device[]>(res);
}

export async function fetchDevice(deviceId: string): Promise<Device> {
  const res = await fetch(buildUrl(`/devices/${deviceId}`));
  return parseJson<Device>(res);
}

export async function fetchFacets(params: { q?: string }): Promise<FacetsResponse> {
  const res = await fetch(buildUrl("/devices/facets", params));
  return parseJson<FacetsResponse>(res);
}

export async function fetchCurrentUser(token: string): Promise<UserSelf> {
  const res = await fetch(buildUrl("/users/me"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<UserSelf>(res);
}

export async function fetchUsersAdmin(token: string): Promise<UserSelf[]> {
  const res = await fetch(buildUrl("/users"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<UserSelf[]>(res);
}

export async function updateUserAdmin(
  token: string,
  userId: string,
  body: UserUpdateBody,
): Promise<UserSelf> {
  const res = await fetch(buildUrl(`/users/${userId}`), {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseJson<UserSelf>(res);
}

export async function fetchReservations(token: string): Promise<Reservation[]> {
  const res = await fetch(buildUrl("/reservations"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<Reservation[]>(res);
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
