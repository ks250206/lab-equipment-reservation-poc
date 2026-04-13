/** クエリのキー順を無視して `?a=1&b=2` と `?b=2&a=1` を同一とみなす。 */
export function urlSearchEqual(a: string, b: string): boolean {
  const norm = (raw: string) => {
    const s = raw.startsWith("?") ? raw.slice(1) : raw;
    const sp = new URLSearchParams(s);
    const keys = [...new Set(sp.keys())].sort();
    const out = new URLSearchParams();
    for (const k of keys) {
      const v = sp.get(k);
      if (v !== null && v !== "") out.set(k, v);
    }
    return out.toString();
  };
  return norm(a) === norm(b);
}
