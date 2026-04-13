/**
 * FullCalendar の `select` で得られる区間は `end` が排他的（区間は [start, end)）。
 * バックエンドの `start_time` / `end_time` はその解釈で送る（重複判定と整合）。
 */
export function assertFcSelectRangeValid(start: Date, end: Date): void {
  if (
    !(start instanceof Date) ||
    !(end instanceof Date) ||
    Number.isNaN(start.getTime()) ||
    Number.isNaN(end.getTime())
  ) {
    throw new Error("日付が無効です");
  }
  if (start.getTime() >= end.getTime()) {
    throw new Error("終了は開始より後である必要があります");
  }
}
