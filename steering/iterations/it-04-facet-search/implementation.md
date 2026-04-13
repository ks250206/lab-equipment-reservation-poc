# 実装内容（イテレーション 4 — ファセット検索）

## スコープ

- **`search_devices` サービス**: 任意の全文クエリ（`q`）に加え、`category`、`location`、`status` を SQLAlchemy の `ilike`／等値でフィルタ。
- **`get_facets`**: 現在の結果集合について各次元ごとの件数を集計（カテゴリ・場所・ステータス）。
- **HTTP**: `GET /api/devices` でファセット用クエリを受け付け、`GET /api/devices/facets` でファセット用ペイロードを返却。
- **`tests/test_facet_search.py`** による検索＋ファセットの振る舞いテスト。
