"""一覧 API 共通のページサイズ（クエリ文字列からの解釈用）。"""

from enum import IntEnum


class ListPageSize(IntEnum):
    TWENTY = 20
    FIFTY = 50
    HUNDRED = 100
