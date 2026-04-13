import type { DateSelectArg, DatesSetArg, EventClickArg, EventMountArg } from "@fullcalendar/core";
import jaLocale from "@fullcalendar/core/locales/ja.js";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { Pencil } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { addMonths, format, startOfMonth } from "date-fns";
import { ja } from "date-fns/locale";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { fetchDeviceReservations, fetchDeviceReservationsAllInRange } from "@/api/client";
import type { PageSize, Reservation } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { ListPaginationBar } from "@/components/ListPaginationBar";
import {
  DeviceReservationSlotCreateDialog,
  type DeviceReservationCreateRange,
} from "@/components/device/DeviceReservationSlotCreateDialog";
import { ReservationDetailDialog } from "@/components/device/ReservationDetailDialog";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { assertFcSelectRangeValid } from "@/lib/fullCalendarSelection";
import {
  reservationsToFullCalendarEvents,
  type DeviceReservationCalendarExtendedProps,
} from "@/lib/deviceReservationCalendar";

type ViewMode = "list" | "month" | "week" | "day";

function initialCalendarMonthRange() {
  const n = new Date();
  return { start: startOfMonth(n), end: startOfMonth(addMonths(n, 1)) };
}

export function DeviceReservationsSection({ deviceId }: { deviceId: string }) {
  const { authenticated, ready, login, getValidToken } = useAuth();
  const meQuery = useCurrentUser();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [queryRange, setQueryRange] = useState(initialCalendarMonthRange);
  const [listPage, setListPage] = useState(1);
  const [listPageSize, setListPageSize] = useState<PageSize>(50);
  const [listMineOnly, setListMineOnly] = useState(false);
  const [listReservationStatus, setListReservationStatus] = useState<
    "" | "confirmed" | "cancelled" | "completed"
  >("");
  const [modalReservation, setModalReservation] = useState<Reservation | null>(null);
  const [modalEditable, setModalEditable] = useState(false);
  const [createRange, setCreateRange] = useState<DeviceReservationCreateRange | null>(null);
  const calendarRef = useRef<FullCalendar>(null);

  const onDatesSet = useCallback((arg: DatesSetArg) => {
    setQueryRange((prev) => {
      if (
        prev.start.getTime() === arg.start.getTime() &&
        prev.end.getTime() === arg.end.getTime()
      ) {
        return prev;
      }
      return { start: arg.start, end: arg.end };
    });
  }, []);

  useEffect(() => {
    if (viewMode === "list") return;
    const api = calendarRef.current?.getApi();
    if (!api) return;
    const name =
      viewMode === "month" ? "dayGridMonth" : viewMode === "week" ? "timeGridWeek" : "timeGridDay";
    if (api.view.type !== name) {
      api.changeView(name);
    }
  }, [viewMode]);

  useEffect(() => {
    setListPage(1);
  }, [queryRange.start, queryRange.end]);

  useEffect(() => {
    setListPage(1);
  }, [listPageSize]);

  useEffect(() => {
    setListPage(1);
  }, [listMineOnly, listReservationStatus]);

  const listReservationsQuery = useQuery({
    queryKey: [
      "device-reservations",
      deviceId,
      queryRange.start.toISOString(),
      queryRange.end.toISOString(),
      "list",
      listPage,
      listPageSize,
      listMineOnly,
      listReservationStatus,
    ],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) {
        throw new Error("ログインが必要です");
      }
      return fetchDeviceReservations(token, deviceId, {
        from: queryRange.start.toISOString(),
        to: queryRange.end.toISOString(),
        page: listPage,
        page_size: listPageSize,
        mineOnly: listMineOnly,
        reservationStatus: listReservationStatus || undefined,
      });
    },
    enabled: Boolean(deviceId) && authenticated && ready && viewMode === "list",
  });

  const calendarReservationsQuery = useQuery({
    queryKey: [
      "device-reservations",
      deviceId,
      queryRange.start.toISOString(),
      queryRange.end.toISOString(),
      "calendar",
    ],
    queryFn: async () => {
      const token = await getValidToken();
      if (!token) {
        throw new Error("ログインが必要です");
      }
      return fetchDeviceReservationsAllInRange(token, deviceId, {
        from: queryRange.start.toISOString(),
        to: queryRange.end.toISOString(),
      });
    },
    enabled: Boolean(deviceId) && authenticated && ready && viewMode !== "list",
  });

  useEffect(() => {
    if (!listReservationsQuery.isSuccess || !listReservationsQuery.data) return;
    const totalPages = Math.max(1, Math.ceil(listReservationsQuery.data.total / listPageSize));
    if (listPage > totalPages) setListPage(totalPages);
  }, [listReservationsQuery.isSuccess, listReservationsQuery.data, listPage, listPageSize]);

  const myUserId = meQuery.data?.id;

  const calendarEvents = useMemo(
    () => reservationsToFullCalendarEvents(calendarReservationsQuery.data ?? [], myUserId),
    [calendarReservationsQuery.data, myUserId],
  );

  const onEventClick = useCallback((arg: EventClickArg) => {
    const ext = arg.event.extendedProps as DeviceReservationCalendarExtendedProps;
    if (!ext?.reservation) return;
    arg.jsEvent.preventDefault();
    setModalReservation(ext.reservation);
    setModalEditable(Boolean(ext.isMine));
  }, []);

  const onEventDidMount = useCallback((arg: EventMountArg) => {
    const ext = arg.event.extendedProps as DeviceReservationCalendarExtendedProps;
    const tip = ext?.tooltipTitle;
    if (tip) {
      arg.el.setAttribute("title", tip);
    }
  }, []);

  const onSelect = useCallback((selectInfo: DateSelectArg) => {
    selectInfo.view.calendar.unselect();
    try {
      assertFcSelectRangeValid(selectInfo.start, selectInfo.end);
    } catch {
      return;
    }
    setCreateRange({
      start: selectInfo.start,
      end: selectInfo.end,
      allDay: selectInfo.allDay,
    });
  }, []);

  const shiftListMonth = (delta: number) => {
    setQueryRange((r) => ({
      start: addMonths(r.start, delta),
      end: addMonths(r.end, delta),
    }));
  };

  if (!ready) {
    return <p className="text-sm text-zinc-600">認証を確認しています…</p>;
  }

  if (!authenticated) {
    return (
      <div className="space-y-3 rounded-lg border border-zinc-200 bg-zinc-50 p-4">
        <h2 className="text-lg font-medium text-zinc-800">この装置の予約</h2>
        <p className="text-sm text-zinc-700">
          占有枠の一覧を表示するにはログインが必要です（他ユーザーの予約も表示されます）。
        </p>
        <button
          type="button"
          className="rounded border border-zinc-300 bg-white px-4 py-2 text-sm hover:bg-zinc-50"
          onClick={() => login()}
        >
          ログイン
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-medium text-zinc-800">この装置の予約</h2>
        <div className="flex flex-wrap gap-1">
          {(
            [
              ["list", "リスト"],
              ["month", "月"],
              ["week", "週"],
              ["day", "日"],
            ] as const
          ).map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              onClick={() => setViewMode(mode)}
              className={
                viewMode === mode
                  ? "rounded border border-zinc-800 bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white"
                  : "rounded border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {viewMode === "list" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-zinc-600">リスト表示</span>
            <button
              type="button"
              onClick={() => setListMineOnly(false)}
              className={
                !listMineOnly
                  ? "rounded border border-zinc-800 bg-zinc-800 px-3 py-1 text-xs font-medium text-white"
                  : "rounded border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              }
            >
              すべて
            </button>
            <button
              type="button"
              onClick={() => setListMineOnly(true)}
              className={
                listMineOnly
                  ? "rounded border border-teal-800 bg-teal-700 px-3 py-1 text-xs font-medium text-white"
                  : "rounded border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              }
            >
              自分のみ
            </button>
            <label className="inline-flex items-center gap-2 text-xs text-zinc-700">
              <span className="font-medium">ステータス</span>
              <select
                value={listReservationStatus}
                onChange={(e) =>
                  setListReservationStatus(
                    e.target.value as "" | "confirmed" | "cancelled" | "completed",
                  )
                }
                className="rounded border border-zinc-300 bg-white px-2 py-1"
              >
                <option value="">（指定なし）</option>
                <option value="confirmed">確定</option>
                <option value="cancelled">キャンセル</option>
                <option value="completed">完了</option>
              </select>
            </label>
          </div>
          <div className="flex items-center justify-between gap-2 text-sm">
            <button
              type="button"
              className="rounded border border-zinc-300 bg-white px-3 py-1 hover:bg-zinc-50"
              onClick={() => shiftListMonth(-1)}
            >
              前月
            </button>
            <span className="font-medium text-zinc-700">
              {format(queryRange.start, "yyyy年 M月", { locale: ja })}
            </span>
            <button
              type="button"
              className="rounded border border-zinc-300 bg-white px-3 py-1 hover:bg-zinc-50"
              onClick={() => shiftListMonth(1)}
            >
              翌月
            </button>
          </div>
        </div>
      )}

      {viewMode === "list" && listReservationsQuery.isError && (
        <p className="text-sm text-red-700">
          {listReservationsQuery.error instanceof Error
            ? listReservationsQuery.error.message
            : "予約を読み込めませんでした。"}
        </p>
      )}

      {viewMode !== "list" && calendarReservationsQuery.isError && (
        <p className="text-sm text-red-700">
          {calendarReservationsQuery.error instanceof Error
            ? calendarReservationsQuery.error.message
            : "予約を読み込めませんでした。"}
        </p>
      )}

      {viewMode === "list" && listReservationsQuery.isLoading && (
        <p className="text-sm text-zinc-600">予約を読み込み中…</p>
      )}

      {viewMode !== "list" && calendarReservationsQuery.isLoading && (
        <p className="text-sm text-zinc-600">カレンダー用の予約を読み込み中…</p>
      )}

      {viewMode === "list" && listReservationsQuery.isSuccess && (
        <div className="space-y-3">
          <ListPaginationBar
            total={listReservationsQuery.data.total}
            page={listPage}
            pageSize={listPageSize}
            onPageChange={setListPage}
            onPageSizeChange={setListPageSize}
          />
          <div className="overflow-x-auto rounded-lg border border-zinc-200">
            <table className="min-w-full border-collapse text-sm">
              <thead className="bg-zinc-50 text-left text-zinc-600">
                <tr>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">開始</th>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">終了</th>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">ステータス</th>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">目的</th>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">氏名</th>
                  <th className="border-b border-zinc-200 px-3 py-2 font-medium">メール</th>
                  <th className="w-14 border-b border-zinc-200 px-2 py-2 text-center font-medium">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {listReservationsQuery.data.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-zinc-500">
                      この期間に予約はありません。
                    </td>
                  </tr>
                ) : (
                  listReservationsQuery.data.items.map((r) => {
                    const mine = myUserId !== undefined && r.user_id === myUserId;
                    return (
                      <tr key={r.id} className={mine ? "bg-amber-50/80" : undefined}>
                        <td className="border-b border-zinc-100 px-3 py-2">
                          {format(new Date(r.start_time), "PPp", { locale: ja })}
                        </td>
                        <td className="border-b border-zinc-100 px-3 py-2">
                          {format(new Date(r.end_time), "PPp", { locale: ja })}
                        </td>
                        <td className="border-b border-zinc-100 px-3 py-2">{r.status}</td>
                        <td className="border-b border-zinc-100 px-3 py-2">
                          {r.purpose?.trim() ? r.purpose : "—"}
                        </td>
                        <td className="border-b border-zinc-100 px-3 py-2 text-zinc-800">
                          {r.user_name?.trim() ? r.user_name.trim() : "—"}
                          {mine ? (
                            <span className="ml-2 rounded bg-amber-200/80 px-1.5 py-0.5 text-[10px] font-sans text-amber-900">
                              自分
                            </span>
                          ) : null}
                        </td>
                        <td className="border-b border-zinc-100 px-3 py-2 break-all text-xs text-zinc-700">
                          {r.user_email?.trim() ? r.user_email.trim() : "—"}
                        </td>
                        <td className="border-b border-zinc-100 px-2 py-2 text-center">
                          <button
                            type="button"
                            className="inline-flex rounded border border-zinc-300 bg-white p-1.5 text-zinc-700 hover:bg-zinc-50"
                            aria-label={mine ? "自分の予約を編集" : "予約の詳細"}
                            onClick={() => {
                              setModalReservation(r);
                              setModalEditable(mine);
                            }}
                          >
                            <Pencil className="h-4 w-4" aria-hidden />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {viewMode !== "list" && (
        <div className="rounded-lg border border-zinc-200 bg-white p-2">
          <FullCalendar
            ref={calendarRef}
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            locale={jaLocale}
            initialView={
              viewMode === "month"
                ? "dayGridMonth"
                : viewMode === "week"
                  ? "timeGridWeek"
                  : "timeGridDay"
            }
            initialDate={queryRange.start}
            headerToolbar={{ left: "prev,next today", center: "title", right: "" }}
            datesSet={onDatesSet}
            events={calendarEvents}
            eventClick={onEventClick}
            eventDidMount={onEventDidMount}
            views={{
              dayGridMonth: {
                dayMaxEvents: 3,
                moreLinkContent: (arg) => `+${arg.num}件`,
              },
            }}
            height="auto"
            editable={false}
            selectable
            selectMirror
            selectOverlap={false}
            select={onSelect}
            eventDisplay="block"
            slotEventOverlap={false}
          />
        </div>
      )}

      <p className="text-sm text-zinc-600">
        カレンダーでは<strong className="font-medium text-teal-800">自分の予約はティール系</strong>
        、他ユーザーの枠はスレート系で色分けしています。空き枠をドラッグしてこの装置の予約を作成できます（既存予約と重なる範囲は選択できません）。
        取り消しや一覧は{" "}
        <Link to="/reservations" className="text-blue-800 underline">
          予約一覧
        </Link>
        から行えます。
      </p>

      <DeviceReservationSlotCreateDialog
        open={createRange !== null}
        onOpenChange={(next) => {
          if (!next) {
            setCreateRange(null);
          }
        }}
        deviceId={deviceId}
        range={createRange}
        getValidToken={getValidToken}
      />

      <ReservationDetailDialog
        open={modalReservation !== null}
        onOpenChange={(next) => {
          if (!next) {
            setModalReservation(null);
          }
        }}
        reservation={modalReservation}
        editable={modalEditable}
        deviceId={deviceId}
        getValidToken={getValidToken}
      />
    </div>
  );
}
