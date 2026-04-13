# steering（イテレーション作業場）

設計の SSOT は `doc/`、エージェントの必須ルールは `AGENTS.md`。ここは **イテレーション単位の作業ログ・TODO・実装メモ** 用で、都度更新してよい。

## ディレクトリ構成

| パス | 用途 |
|------|------|
| [planning/initial-plan.md](planning/initial-plan.md) | PoC 全体の初期メモ（ロードマップの種） |
| `iterations/it-NN-<slug>/` | 各イテレーションの作業単位（下記 3 ファイル） |

`NN` は `AGENTS.md` のイテレーション一覧と同じ番号（2 桁ゼロ埋め）。`<slug>` は短い **kebab-case の英語**（例: `database-auth`）。

## イテレーション着手順（必須）

**実装・設定変更・恒久的 `doc/` 変更のいずれかを始める前に**、[@doc/development-guidelines.md](../doc/development-guidelines.md) の「5.3 イテレーション開始時の steering」に従い、当該 `it-NN-<slug>/` と 3 ファイルを用意する。テンプレは [planning/iteration-starter.md](planning/iteration-starter.md)。

## 各イテレーションで揃える 3 ファイル

| ファイル | 言語 | 内容 |
|----------|------|------|
| `implementation.md` | **英語** | そのイテレーションで **実際に入れた実装・到達点**（スコープの要約、主要 PR / コミットの説明）。 |
| `todo.md` | 日本語で可 | チェックリスト。**完了したら `[x]` に更新**する。 |
| `work_report.md` | 日本語で可 | 作業セッションのメモ（判断・詰まり・次アクション）。長文不要。 |

既存フォルダのコピーではなく **新規ディレクトリ**として `iterations/it-NN-<slug>/` を作り、上記 3 ファイルを置く（中身は着手後に追記でよいが、**フォルダと 3 ファイルの存在は着手前必須**）。

## インデックス（フォルダ名）

| # | ディレクトリ | 日本語（AGENTS 対応） |
|---|----------------|----------------------|
| 1 | `iterations/it-01-foundation/` | 基盤構築 |
| 2 | `iterations/it-02-database-auth/` | DB + 認証 |
| 3 | `iterations/it-03-device-crud/` | 装置 CRUD |
| 4 | `iterations/it-04-facet-search/` | ファセット検索 |
| 5 | `iterations/it-05-reservation/` | 予約機能 |
| 6 | `iterations/it-06-frontend/` | フロントエンド |
| 7 | `iterations/it-07-refactor/` | リファクタリング |
| 8 | `iterations/it-08-just-runner/` | タスクランナー（just） |
| 9 | `iterations/it-09-persistence-seed/` | 永続化プロファイル・開発シード |

旧来ルート直下の `01_*.md` 形式は廃止し、内容は必要に応じて各 `work_report.md` / `todo.md` に取り込んだ。
