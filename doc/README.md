# 恒久的ドキュメント（`doc/`）

アプリケーションの「何を作るか」「どう作るか」を定義する。方針が変わらない限りはコードと同期して維持する。

エージェント向けの**必須ルールのみ**はリポジトリルートの [AGENTS.md](../AGENTS.md) にある。ここは詳細 SSOT である。

| ファイル | 内容 |
|----------|------|
| [product-requirements.md](product-requirements.md) | プロダクト要求（ビジョン、機能、受け入れ条件、NFR への参照） |
| [functional-design.md](functional-design.md) | 機能設計（構成図、データモデル、API、認証） |
| [architecture.md](architecture.md) | 技術仕様（スタック、ツール、制約、パフォーマンス） |
| [repository-structure.md](repository-structure.md) | リポジトリ構造と配置ルール |
| [development-guidelines.md](development-guidelines.md) | 開発ガイドライン（コーディング、テスト、Git、イテレーション） |
| [glossary.md](glossary.md) | ユビキタス言語 |

チャットやエディタで参照するときは `@doc/<上記ファイル名>` と書く（例: `@doc/functional-design.md`）。
