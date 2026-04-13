/** FastAPI のエラー JSON（`{ "detail": ... }`）からユーザー向け文言を組み立てる。 */
export function messageFromApiErrorBody(status: number, bodyText: string): string {
  const raw = bodyText.trim();
  if (!raw) {
    return status ? `リクエストに失敗しました（HTTP ${status}）` : "リクエストに失敗しました";
  }
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    return formatFastApiDetail(parsed.detail, raw);
  } catch {
    return raw.length > 280 ? `${raw.slice(0, 280)}…` : raw;
  }
}

function formatFastApiDetail(detail: unknown, fallbackRaw: string): string {
  if (detail === undefined || detail === null) {
    return fallbackRaw.length > 280 ? `${fallbackRaw.slice(0, 280)}…` : fallbackRaw;
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "object" && item !== null && "msg" in item) {
        const msg = (item as { msg?: unknown }).msg;
        return typeof msg === "string" ? msg : JSON.stringify(item);
      }
      return String(item);
    });
    const joined = parts.join(" ");
    return joined || fallbackRaw;
  }
  if (typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return String(detail);
}
