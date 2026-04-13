import type { EventInput } from "@fullcalendar/core";

import type { Reservation } from "@/api/types";

export function reservationsToFullCalendarEvents(reservations: Reservation[]): EventInput[] {
  return reservations.map((r) => ({
    id: r.id,
    title: r.purpose?.trim() ? r.purpose : "予約",
    start: r.start_time,
    end: r.end_time,
  }));
}
