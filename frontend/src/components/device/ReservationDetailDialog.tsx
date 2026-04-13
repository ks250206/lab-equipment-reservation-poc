import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ja } from "date-fns/locale";
import { useEffect, useState } from "react";

import { updateReservation } from "@/api/client";
import type { Reservation } from "@/api/types";
import { isoToDatetimeLocalValue, localDatetimeInputToIso } from "@/lib/datetimeLocal";

const RESERVATION_STATUSES = ["confirmed", "cancelled", "completed"] as const;

type ReservationDetailDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reservation: Reservation | null;
  editable: boolean;
  deviceId: string;
  getValidToken: () => Promise<string | null>;
};

export function ReservationDetailDialog({
  open,
  onOpenChange,
  reservation,
  editable,
  deviceId,
  getValidToken,
}: ReservationDetailDialogProps) {
  const queryClient = useQueryClient();
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [purpose, setPurpose] = useState("");
  const [status, setStatus] = useState<string>("confirmed");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!reservation || !open) return;
    setStartLocal(isoToDatetimeLocalValue(reservation.start_time));
    setEndLocal(isoToDatetimeLocalValue(reservation.end_time));
    setPurpose(reservation.purpose ?? "");
    setStatus(reservation.status);
    setFormError(null);
  }, [reservation, open]);

  const updateMut = useMutation({
    mutationFn: async () => {
      if (!reservation) throw new Error("予約がありません");
      const token = await getValidToken();
      if (!token) throw new Error("ログイン情報が無効です");
      return updateReservation(token, reservation.id, {
        start_time: localDatetimeInputToIso(startLocal),
        end_time: localDatetimeInputToIso(endLocal),
        purpose: purpose.trim() || null,
        status,
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

  const displayName = reservation
    ? reservation.user_name?.trim() || reservation.user_email?.trim() || "（名前なし）"
    : "";
  const displayEmail = reservation?.user_email?.trim() || "—";

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {reservation ? (
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-[min(100vw-2rem,28rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-4 shadow-lg outline-none">
            <Dialog.Title className="text-lg font-medium text-zinc-900">
              {editable ? "予約の編集" : "予約の詳細"}
            </Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-zinc-600">
              {editable ? "内容を変更して保存できます。" : "閲覧のみです。"}
            </Dialog.Description>

            <div className="mt-4 space-y-3 text-sm">
              {!editable ? (
                <>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">開始</p>
                    <p className="text-zinc-800">
                      {format(new Date(reservation.start_time), "PPp", { locale: ja })}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">終了</p>
                    <p className="text-zinc-800">
                      {format(new Date(reservation.end_time), "PPp", { locale: ja })}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">ステータス</p>
                    <p className="text-zinc-800">{reservation.status}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">目的</p>
                    <p className="text-zinc-800">
                      {reservation.purpose?.trim() ? reservation.purpose : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">氏名</p>
                    <p className="text-zinc-800">{displayName}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-zinc-500">メール</p>
                    <p className="break-all text-zinc-800">{displayEmail}</p>
                  </div>
                </>
              ) : (
                <>
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
                    <span className="text-xs font-medium text-zinc-600">ステータス</span>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                      className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                    >
                      {RESERVATION_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs font-medium text-zinc-600">目的</span>
                    <textarea
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      rows={3}
                      className="w-full rounded border border-zinc-300 px-3 py-2 text-sm"
                    />
                  </label>
                  <div className="rounded bg-zinc-50 p-2 text-xs text-zinc-600">
                    <p>氏名: {displayName}</p>
                    <p className="break-all">メール: {displayEmail}</p>
                  </div>
                </>
              )}
            </div>

            {formError ? <p className="mt-3 text-sm text-red-700">{formError}</p> : null}

            <div className="mt-6 flex justify-end gap-2">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm hover:bg-zinc-50"
                >
                  閉じる
                </button>
              </Dialog.Close>
              {editable ? (
                <button
                  type="button"
                  disabled={updateMut.isPending}
                  onClick={() => updateMut.mutate()}
                  className="rounded bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-60"
                >
                  {updateMut.isPending ? "保存中…" : "保存"}
                </button>
              ) : null}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      ) : null}
    </Dialog.Root>
  );
}
