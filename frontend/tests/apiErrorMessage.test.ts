import { describe, expect, it } from "vitest";

import { messageFromApiErrorBody } from "@/lib/apiErrorMessage";

describe("messageFromApiErrorBody", () => {
  it("文字列の detail をそのまま返す", () => {
    const body = JSON.stringify({ detail: "時間が重なっています" });
    expect(messageFromApiErrorBody(409, body)).toBe("時間が重なっています");
  });

  it("422 形式の配列 detail を結合する", () => {
    const body = JSON.stringify({
      detail: [{ loc: ["body", "x"], msg: "field required", type: "value_error" }],
    });
    expect(messageFromApiErrorBody(422, body)).toBe("field required");
  });

  it("JSON でないときは先頭を返す", () => {
    const raw = "not json at all";
    expect(messageFromApiErrorBody(500, raw)).toBe(raw);
  });

  it("空本文のときは HTTP ステータスを含む", () => {
    expect(messageFromApiErrorBody(503, "   ")).toBe("リクエストに失敗しました（HTTP 503）");
  });
});
