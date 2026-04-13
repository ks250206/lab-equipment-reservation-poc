import { afterAll, beforeAll, describe, expect, it } from "vitest";

import type { Reservation } from "../src/api/types";
import {
  reservationCalendarTooltipTitle,
  reservationDisplayName,
  reservationsToFullCalendarEvents,
} from "../src/lib/deviceReservationCalendar";

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
  const prevTz = process.env.TZ;

  beforeAll(() => {
    process.env.TZ = "UTC";
  });

  afterAll(() => {
    process.env.TZ = prevTz;
  });

  it("表示タイトルは氏名のみ", () => {
    const events = reservationsToFullCalendarEvents([
      {
        ...baseReservation,
        user_name: "山田",
        user_email: "yamada@example.com",
      },
    ]);
    expect(events[0]?.title).toBe("山田");
  });

  it("氏名が空のときメールをタイトルに含める", () => {
    const events = reservationsToFullCalendarEvents([
      { ...baseReservation, user_name: null, user_email: "only@example.com" },
    ]);
    expect(events[0]?.title).toBe("only@example.com");
  });

  it("氏名・メールが空のときフォールバック文言", () => {
    const events = reservationsToFullCalendarEvents([
      { ...baseReservation, user_name: null, user_email: null },
    ]);
    expect(events[0]?.title).toBe("（名前なし）");
  });

  it("extendedProps に予約・isMine・tooltipTitle（時刻+氏名）を載せる", () => {
    const mineId = baseReservation.user_id;
    const events = reservationsToFullCalendarEvents(
      [
        {
          ...baseReservation,
          user_name: "山田",
          user_email: "yamada@example.com",
        },
      ],
      mineId,
    );
    expect(events[0]?.extendedProps).toMatchObject({
      isMine: true,
      tooltipTitle: "10:00–11:00 山田",
    });
  });

  it("myUserId が一致しないとき isMine は false", () => {
    const events = reservationsToFullCalendarEvents(
      [baseReservation],
      "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    );
    expect(events[0]?.extendedProps).toMatchObject({ isMine: false });
  });
});

describe("reservationDisplayName", () => {
  it("氏名優先", () => {
    expect(
      reservationDisplayName({
        ...baseReservation,
        user_name: "  佐藤  ",
        user_email: "sato@example.com",
      }),
    ).toBe("佐藤");
  });
});

describe("reservationCalendarTooltipTitle", () => {
  it("ホバー用に時刻レンジと表示名を結合する", () => {
    expect(
      reservationCalendarTooltipTitle({
        ...baseReservation,
        user_name: "山田",
        user_email: "yamada@example.com",
      }),
    ).toBe("10:00–11:00 山田");
  });
});
