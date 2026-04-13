import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { createReservation } from "@/api/client";
import { isoToDatetimeLocalValue, localDatetimeInputToIso } from "@/lib/datetimeLocal";
import { assertFcSelectRangeValid } from "@/lib/fullCalendarSelection";

export type DeviceReservationCreateRange = {
  start: Date;
  end: Date;
  allDay: boolean;
};

type DeviceReservationSlotCreateDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceId: string;
  range: DeviceReservationCreateRange | null;
  getValidToken: () => Promise<string | null>;
};

export function DeviceReservationSlotCreateDialog({
  open,
  onOpenChange,
  deviceId,
  range,
  getValidToken,
}: DeviceReservationSlotCreateDialogProps) {
  const queryClient = useQueryClient();
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [purpose, setPurpose] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!range || !open) return;
    try {
      assertFcSelectRangeValid(range.start, range.end);
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "無効な範囲です");
      return;
    }
    setStartLocal(isoToDatetimeLocalValue(range.start.toISOString()));
    setEndLocal(isoToDatetimeLocalValue(range.end.toISOString()));
    setPurpose("");
    setFormError(null);
  }, [range, open]);

  const createMut = useMutation({
    mutationFn: async () => {
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      return createReservation(token, {
        device_id: deviceId,
        start_time: localDatetimeInputToIso(startLocal),
        end_time: localDatetimeInputToIso(endLocal),
        purpose: purpose.trim() || undefined,
      });
    },
    onSuccess: () => {
      setFormError(null);
      void queryClient.invalidateQueries({ queryKey: ["device-reservations", deviceId] });
      void queryClient.invalidateQueries({ queryKey: ["reservations"] });
      onOpenChange(false);
    },
    onError: (e: Error) => {
      setFormError(e.message);
    },
  });

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {range ? (
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-[min(100vw-2rem,28rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-4 shadow-lg outline-none">
            <Dialog.Title className="text-lg font-medium text-zinc-900">予約を作成</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-zinc-600">
              カレンダーで選択した範囲が開始・終了に設定されています。必要に応じて修正してから作成してください。
              {range.allDay ? (
                <span className="mt-1 block text-xs text-zinc-500">（全日枠の選択）</span>
              ) : null}
            </Dialog.Description>

            <div className="mt-4 grid gap-3 text-sm">
              <label className="block space-y-1">
                <span className="text-xs font-medium text-zinc-600">開始</span>
                <input
                  type="datetime-local"
                  value={startLocal}
                  onChange={(e) => setStartLocal(e.target.value)}
                  className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-zinc-600">終了</span>
                <input
                  type="datetime-local"
                  value={endLocal}
                  onChange={(e) => setEndLocal(e.target.value)}
                  className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-zinc-600">目的（任意）</span>
                <textarea
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  rows={2}
                  className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                />
              </label>
            </div>

            {formError ? <p className="mt-3 text-sm text-red-700">{formError}</p> : null}

            <div className="mt-6 flex justify-end gap-2">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm hover:bg-zinc-50"
                >
                  キャンセル
                </button>
              </Dialog.Close>
              <button
                type="button"
                disabled={createMut.isPending}
                onClick={() => {
                  setFormError(null);
                  try {
                    const s = localDatetimeInputToIso(startLocal);
                    const e = localDatetimeInputToIso(endLocal);
                    if (new Date(s).getTime() >= new Date(e).getTime()) {
                      setFormError("終了は開始より後である必要があります");
                      return;
                    }
                  } catch (err) {
                    setFormError(err instanceof Error ? err.message : "日時が無効です");
                    return;
                  }
                  createMut.mutate();
                }}
                className="rounded bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
              >
                {createMut.isPending ? "作成中…" : "予約する"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      ) : null}
    </Dialog.Root>
  );
}
