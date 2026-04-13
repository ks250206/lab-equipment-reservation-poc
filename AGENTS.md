# AGENTS.md

## このファイルの役割

AI コーディングエージェントが**必ず守るべきルール**だけをここに書く。  
製品要求・機能設計・API／DB 定義・ディレクトリ詳細・開発作業手順などの**恒久的な SSOT**は `doc/` に置く。

### `doc/` の参照のしかた（`@` 記法）

実装や調査の前に、必要なドキュメントを読む。エディタやチャットでファイルを指定するときは、リポジトリルートからの相対パスで **`@doc/ファイル名`** と書く（例: `@doc/functional-design.md`）。  
Markdown リンクとして開く場合は次の一覧のパスを使う。

| ドキュメント | `@` 記法の例 | ファイル |
|-------------|----------------|----------|
| プロダクト要求定義 | `@doc/product-requirements.md` | [doc/product-requirements.md](doc/product-requirements.md) |
| 機能設計（構成・データモデル・API） | `@doc/functional-design.md` | [doc/functional-design.md](doc/functional-design.md) |
| 技術仕様・アーキテクチャ | `@doc/architecture.md` | [doc/architecture.md](doc/architecture.md) |
| リポジトリ構造 | `@doc/repository-structure.md` | [doc/repository-structure.md](doc/repository-structure.md) |
| 開発ガイドライン（テスト・Git・イテレーション等） | `@doc/development-guidelines.md` | [doc/development-guidelines.md](doc/development-guidelines.md) |
| ローカル開発（Nix + just・Compose・シード） | `@doc/local-development.md` | [doc/local-development.md](doc/local-development.md) |
| 本番運用の指針 | `@doc/production-operations.md` | [doc/production-operations.md](doc/production-operations.md) |
| ユビキタス言語 | `@doc/glossary.md` | [doc/glossary.md](doc/glossary.md) |

---

## 必須ルール（Must）

1. **設計に従う**: 実装は `doc/` の内容と矛盾しないこと。仕様変更がある場合は**先に該当する `doc/*.md` を更新**してからコードを合わせる（どのファイルを直すかは [@doc/development-guidelines.md](doc/development-guidelines.md) の「ドキュメント更新の責務」を参照）。
2. **用語**: ドメイン用語・列挙値の表記は [@doc/glossary.md](doc/glossary.md) を正とする。
3. **テスト**: モックを使わないこと。カバレッジ目標とコマンドは [@doc/development-guidelines.md](doc/development-guidelines.md) に従う。
4. **変更範囲**: 依頼内容に必要な最小限の変更にとどめ、無関係なリファクタやファイル移動をしない。
5. **一貫性**: 既存コードの import 形式・抽象度・コメント量に合わせる。新規だけ別スタイルにしない。
6. **コミット**: 自動生成された実装が常に望ましいとは限らない。**利用者による確認・修正（HITL: Human-in-the-loop）を終えたあと**に、イテレーション単位で `git add` → `git commit` する。エージェントは品質チェックが通った直後に **`git commit` まで勝手に進めない**（利用者がコミットを明示的に依頼した場合はその限りでない）。作業完了の報告時点で未コミットが残っていてもよい。メッセージ形式は [@doc/development-guidelines.md](doc/development-guidelines.md) の Git 規約に従い、番号・コミット目安は下記「イテレーション一覧」と一致させる。
7. **README / 入口ドキュメントの更新**: [README.md](README.md) は人間向けの**短い入口**（Nix + just のクイックスタートと `doc/` へのリンク）にとどめる。**各イテレーション完了時**に見直し、詳細な手順・URL 一覧・永続化の説明などは [doc/local-development.md](doc/local-development.md) や [doc/production-operations.md](doc/production-operations.md) へ寄せ、README は要約とリンクだけに保つ。README または入口ドキュメントに変更があれば**必ず**更新する（変更がない場合はスキップでよいが、見直し自体は省かない）。
8. **本ファイル（AGENTS.md）の更新**: 「必須ルール」の追加・変更・削除、または「イテレーション一覧」のステータス／行の更新があったときに編集する。API・データモデル等の詳細仕様は `doc/` 側へ書き分ける。
9. **イテレーションごとの品質ループ（必須）**: 各イテレーションの区切りごとに、触ったレイヤー（バックエンド／フロントエンドのいずれかまたは両方）について **format → lint → test** を**必ず**実行する（コマンド例は [@doc/development-guidelines.md](doc/development-guidelines.md) の「イテレーション完了時の品質チェック」）。いずれかが失敗したら修正し、**再度同じチェーンを回してすべて成功するまで繰り返す**。
10. **リファクタリングのフィードバックループ（必須）**: 上記の結果や型チェック・レビューで示された問題（重複、責務の混在、ガイドライン違反など）を、[@doc/development-guidelines.md](doc/development-guidelines.md) のリファクタ基準とルール4（最小変更）の両方に従って改善する。改善後に**再度 format → lint → test** を実行し、グリーンを確認する。
11. **イテレーション開始時の steering（必須）**: イテレーション N に着手するときは、**コード・設定・ドキュメントのいずれかを変えるより前**に、[@doc/development-guidelines.md](doc/development-guidelines.md) の「イテレーション開始時の steering」に従い、`steering/iterations/it-NN-<slug>/` に **`implementation.md` / `todo.md` / `work_report.md` の 3 ファイルを必ず作成**する（テンプレは [steering/planning/iteration-starter.md](steering/planning/iteration-starter.md)。**本文は日本語**）。あわせて [AGENTS.md](AGENTS.md) のイテレーション一覧に行 N を追加し、[steering/README.md](steering/README.md) のインデックス表を更新する（未着手または進行中からでよい）。

---

## イテレーション一覧

コミット目安（ブランチ名・タグの参考）と進捗。**完了したら下表のステータスを更新する**（本ファイルの編集はこの一覧と必須ルールに限り、詳細仕様は `doc/` に書く）。

| イテレーション | コミット目安 | ステータス |
|---------------|-------------|-----------|
| 1. 基盤構築 | `it1-init` | 完了 |
| 2. DB + 認証 | `it2-db-auth` | 完了 |
| 3. 装置 CRUD | `it3-device` | 完了 |
| 4. ファセット検索 | `it4-facet` | 完了 |
| 5. 予約機能 | `it5-reservation` | 完了 |
| 6. フロントエンド | `it6-frontend` | 完了 |
| 7. リファクタリング | `it7-refactor` | 完了 |
| 8. タスクランナー（just） | `it8-just` | 完了 |
| 9. 永続化プロファイル・開発シード | `it9-persistence-seed` | 完了 |
| 10. Keycloak ロールベース認可（管理者の正） | `it10-keycloak-rbac` | 完了 |
| 11. users テーブル縮小と Keycloak 正の明文化 | `it11-users-db-slim` | 完了 |
| 12. フロント User ページ・ヘッダー認証 UI | `it12-frontend-user-page` | 完了 |
| 13. 装置ページの予約一覧（リスト / 月・週・日カレンダー） | `it13-device-reservations-views` | 完了 |
| 14. 装置一覧・装置予約リストのページネーション（シード予約拡充） | `it14-list-pagination` | 完了 |
| 15. 予約リストのユーザー表示（DB プロフィール）とシード日付の 2 か月分散 | `it15-reservation-user-profile-seed` | 完了 |
| 16. リスト上ページネーション・カレンダー（時刻+氏名・月省略）・予約詳細モーダル | `it16-reservation-calendar-modal` | 完了 |
| 17. 装置カレンダーのドラッグで予約作成 | `it17-device-calendar-drag-reservation` | 完了 |
| 18. 装置一覧の予約フィルター（ユーザー名・期間）とパンくず・カテゴリ／場所リンク | `it18-device-list-filters-breadcrumb` | 完了 |

---

## 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | 室内装置予約システム PoC — エージェント必須ルール |
| 作成日 | 2026-04-13 |
| 目的 | エージェントが最小のルールセットで安全に実装できるようにする |
