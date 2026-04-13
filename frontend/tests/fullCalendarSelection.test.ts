import { describe, expect, it } from "vitest";

import { assertFcSelectRangeValid } from "../src/lib/fullCalendarSelection";

describe("assertFcSelectRangeValid", () => {
  it("開始が終了より前なら例外を投げない", () => {
    const start = new Date("2026-06-01T10:00:00.000Z");
    const end = new Date("2026-06-01T11:00:00.000Z");
    expect(() => assertFcSelectRangeValid(start, end)).not.toThrow();
  });

  it("開始と終了が同じなら例外", () => {
    const t = new Date("2026-06-01T10:00:00.000Z");
    expect(() => assertFcSelectRangeValid(t, t)).toThrow(/終了は開始より後/);
  });

  it("開始が終了より後なら例外", () => {
    expect(() =>
      assertFcSelectRangeValid(
        new Date("2026-06-01T12:00:00.000Z"),
        new Date("2026-06-01T11:00:00.000Z"),
      ),
    ).toThrow(/終了は開始より後/);
  });
});
