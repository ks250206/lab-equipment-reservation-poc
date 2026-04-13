import { describe, expect, it } from "vitest";

import type { Reservation } from "../src/api/types";
import { reservationsToFullCalendarEvents } from "../src/lib/deviceReservationCalendar";

const baseReservation: Reservation = {
  id: "11111111-1111-1111-1111-111111111111",
  device_id: "22222222-2222-2222-2222-222222222222",
  user_id: "33333333-3333-3333-3333-333333333333",
  start_time: "2026-05-01T10:00:00.000Z",
  end_time: "2026-05-01T11:00:00.000Z",
  purpose: null,
  status: "confirmed",
  created_at: "2026-04-01T00:00:00.000Z",
};

describe("reservationsToFullCalendarEvents", () => {
  it("目的が空のときタイトルは「予約」", () => {
    const events = reservationsToFullCalendarEvents([baseReservation]);
    expect(events).toEqual([
      {
        id: baseReservation.id,
        title: "予約",
        start: baseReservation.start_time,
        end: baseReservation.end_time,
      },
    ]);
  });

  it("目的の文字列をタイトルに使う", () => {
    const events = reservationsToFullCalendarEvents([{ ...baseReservation, purpose: "  試験  " }]);
    expect(events[0]?.title).toBe("  試験  ");
  });
});
