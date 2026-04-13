import { useEffect, useState } from "react";

const DEFAULT_DEBOUNCE_MS = 300;

/**
 * 値のデバウンス。日本語 IME 中は `compositionActive` を true にし、タイマーを起動しない。
 */
export function useDebouncedValue<T>(
  value: T,
  compositionActive: boolean,
  delayMs: number = DEFAULT_DEBOUNCE_MS,
): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    if (compositionActive) return;
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs, compositionActive]);

  return debounced;
}
