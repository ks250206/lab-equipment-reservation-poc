import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "@/hooks/useDebouncedValue";

describe("useDebouncedValue", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("composition が false のときだけ遅延反映する", () => {
    const { result, rerender } = renderHook(
      ({ value, comp }: { value: string; comp: boolean }) => useDebouncedValue(value, comp, 300),
      { initialProps: { value: "a", comp: false } },
    );

    expect(result.current).toBe("a");
    rerender({ value: "ab", comp: false });
    expect(result.current).toBe("a");
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBe("ab");
  });

  it("IME 中はデバウンスしない", () => {
    const { result, rerender } = renderHook(
      ({ value, comp }: { value: string; comp: boolean }) => useDebouncedValue(value, comp, 300),
      { initialProps: { value: "x", comp: false } },
    );

    rerender({ value: "xy", comp: true });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBe("x");

    rerender({ value: "xy", comp: false });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBe("xy");
  });
});
