/** `datetime-local` の値（`YYYY-MM-DDTHH:mm`）を UTC の ISO 8601 に変換する。 */
export function localDatetimeInputToIso(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    throw new Error("日時の形式が正しくありません");
  }
  return d.toISOString();
}

/** UTC ISO を `datetime-local` 用のローカル文字列にする。 */
export function isoToDatetimeLocalValue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "";
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
