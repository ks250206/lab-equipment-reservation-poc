import type { EventInput } from "@fullcalendar/core";
import { format } from "date-fns";

import type { Reservation } from "@/api/types";

export type DeviceReservationCalendarExtendedProps = {
  reservation: Reservation;
  isMine: boolean;
};

export function reservationDisplayName(r: Reservation): string {
  const name = r.user_name?.trim();
  if (name) return name;
  const email = r.user_email?.trim();
  if (email) return email;
  return "（名前なし）";
}

function reservationTimeRangeLabel(r: Reservation): string {
  const start = new Date(r.start_time);
  const end = new Date(r.end_time);
  return `${format(start, "HH:mm")}–${format(end, "HH:mm")}`;
}

export function reservationsToFullCalendarEvents(
  reservations: Reservation[],
  myUserId?: string,
): EventInput[] {
  return reservations.map((r) => ({
    id: r.id,
    title: `${reservationTimeRangeLabel(r)} ${reservationDisplayName(r)}`,
    start: r.start_time,
    end: r.end_time,
    extendedProps: {
      reservation: r,
      isMine: myUserId !== undefined && r.user_id === myUserId,
    } as DeviceReservationCalendarExtendedProps,
  }));
}
