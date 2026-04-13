# Keycloak 初期設定ガイド（PoC 用）

このドキュメントは、**ブラウザで動く React アプリ**が Keycloak でログインできるようにするための、管理コンソールでの作業を順に説明します。表示ラベルは Keycloak のバージョンで多少異なる場合がありますが、**設定すべき項目の意味**は共通です。

**自動設定**: 開発環境では `just seed-dev`（`ENVIRONMENT=development`）が Keycloak 管理 API に接続できた場合、本書と同等の **`device-reservation` 公開クライアント**を冪等で作成・更新します。Keycloak が未起動ならスキップされ、この手順書どおりの手動設定が必要です。

## なぜこの作業が必要か

- フロント（`keycloak-js`）は、Keycloak の **OIDC エンドポイント**にブラウザをリダイレクトしてログインし、**アクセストークン**を取得します。
- そのために Keycloak 側に **「どのアプリからのログインを許可するか」** を登録した **クライアント** が必要です。
- このリポジトリでは `frontend/.env` の **`VITE_KEYCLOAK_CLIENT_ID`**（既定: `device-reservation`）と **同じ Client ID** のクライアントを、**`VITE_KEYCLOAK_REALM`**（既定: `master`）という **レルム** の中に作ります。

用語の対応:

| 用語 | この PoC での例 |
|------|------------------|
| **レルム** | ユーザーやクライアントのまとまり。既定は `master`。`VITE_KEYCLOAK_REALM` と一致させる。 |
| **クライアント** | アプリ単位の登録。SPA 用に **公開クライアント**（クライアントシークレットなし）で作る。 |
| **Valid redirect URIs** | ログイン後にブラウザを戻してよい URL。Vite 開発サーバなら `http://localhost:5173` 配下。 |
| **Web origins** | ブラウザの CORS 用。フロントのオリジン（スキーム＋ホスト＋ポート）を登録する。 |

## 診断: エクスポート JSON でこうなっていたら NG（PKCE 以前の問題）

管理コンソールでクライアントを **JSON でコピー／エクスポート**したとき、次のようになっている場合は **ブラウザ SPA 用ではありません**。PKCE を `S256` にしても直りません。

| JSON のフィールド | NG 例 | あるべき姿（この PoC） |
|--------------------|--------|-------------------------|
| `publicClient` | **`false`** | **`true`**（＝管理画面の **Client authentication: Off**） |
| `clientAuthenticatorType` | **`client-secret`** | 公開クライアントではシークレット認証を使わない（UI では Client authentication **Off**） |
| `secret` | 長い文字列がある | フロントに埋め込めない。**機密クライアント**はサーバ専用向け |

**対処**: **Clients** → **`device-reservation`** → **Capability config**（または設定に「Client authentication」がある画面）で **Client authentication を Off** にし、**Save**。保存後に再度 JSON を見て **`publicClient": true`** になっていることを確認してください。

初回作成ウィザードで **Client authentication を On のまま**進めると、まさに今の JSON の状態になります。必ず **Off** にしてください。

## 事前チェック（ここまでできているか）

1. **`just deps-up`**（または同等）で Keycloak コンテナが起動している。
2. ブラウザで **http://localhost:8080** を開き、Keycloak の画面（ログインまたはトップ）が表示される。
3. **`frontend/.env`** が存在し、少なくとも次が意図どおりか確認する（`frontend/.env.example` が雛形）。

   - `VITE_KEYCLOAK_URL=http://localhost:8080`
   - `VITE_KEYCLOAK_REALM=master`
   - `VITE_KEYCLOAK_CLIENT_ID=device-reservation`

別レルムや別 Client ID にした場合は、**以降の手順で作る名前を `.env` に合わせる**（逆に、手順に合わせて `.env` を直す）必要があります。

## 手順 1: 管理コンソールに入る

1. ブラウザで **http://localhost:8080** を開く。
2. **Administration Console**（管理コンソール）を開く。表示されない場合は **http://localhost:8080/admin/** を試す。
3. ログイン画面が出たら、開発用 compose の既定どおり次を入力する（`compose.dev.yml` の `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`）。

   - **Username**: `admin`
   - **Password**: `admin`

※ 本番相当スタック（`compose.prod.yml`）では、同じ変数名で別パスワードにしている場合があります。そのときは compose の値に合わせてください。

## 手順 2: レルムを選ぶ

1. 左上のレルム名（ドロップダウン）が **`master`** になっていることを確認する。
2. 別レルムを使う場合はここで切り替え、そのレルム名を **`VITE_KEYCLOAK_REALM`** に書く。

このガイドでは **`master` のまま**進めます。

## 手順 3: クライアントを新規作成する

1. 左メニューから **Clients**（クライアント）を開く。
2. **Create client**（クライアントの作成）を押す。

### 画面「General settings」（一般設定）

- **Client type**: **OpenID Connect** のまま（既定でよいことが多い）。
- **Client ID**: **`device-reservation`** と入力する（`VITE_KEYCLOAK_CLIENT_ID` と**完全一致**）。

必要なら **Name** に表示用の名前（例: Device Reservation SPA）を入れる。必須ではない。

**Next**（次へ）を押す。

### 画面「Capability config」（機能・認証方式）

ここが重要です。**ブラウザだけで完結する SPA** 用の設定にします。

- **Client authentication**: **Off**（無効）  
  - **On** のままだと「コンフィデンシャル」クライアントになり、フロントにシークレットを埋め込めないため、この PoC では使わない。
- **Authorization**: 通常は **Off** のままでよい（PoC では不要）。
- **Authentication flow**（名称は環境により「Standard flow」「Standard Flow」など）:
  - **Standard flow**（標準フロー＝認可コードフロー）を **On** にする。  
  - フロントは `keycloak-js` で **PKCE（S256）** を使うため、認可コードフローが必要です。

**Next** を押す。

### 画面「Login settings」（ログイン設定）

リダイレクトと CORS を許可します。

| 項目 | 入力例（Vite 開発サーバ） | 補足 |
|------|---------------------------|------|
| **Root URL** | 空でも可 | 入れるなら `http://localhost:5173` |
| **Home URL** | 空でも可 | |
| **Valid redirect URIs** | **`http://localhost:5173/*`** を追加 | 末尾の `/*` でパス配下をまとめて許可。 |
| **Valid post logout redirect URIs** | **`http://localhost:5173/*`** を追加 | ログアウト後に `window.location.origin` へ戻すため。未設定だとログアウトでエラーになることがある。 |
| **Web origins** | **`http://localhost:5173`** を追加 | **パスは付けない**（オリジンのみ）。複数オリジンなら行を追加。 |

**Vite のプレビュー**（`just frontend-preview`、既定ポート **4173**）も使う場合は、次も**追加**する。

- Valid redirect URIs: `http://localhost:4173/*`
- Valid post logout redirect URIs: `http://localhost:4173/*`
- Web origins: `http://localhost:4173`

**Save**（保存）を押す。

### （推奨）Advanced タブの PKCE

フロントは **PKCE（S256）** で認可コードを交換します。該当クライアントを開き **Advanced**（または詳細）に **Proof Key for Code Exchange Code Challenge Method** がある場合は **`S256`** を選んで保存してください（未設定でも動くことがありますが、明示しておくと環境差に強いです）。

## 手順 4: 動作確認

1. フロントを起動する（例: **`just frontend-dev`**）。バックエンドも API 用に起動しているとよい。
2. **http://localhost:5173** を開く。
3. アプリの **ログイン** を実行し、Keycloak のログイン画面に遷移することを確認する。
4. ログイン後、アプリに戻り、エラーなく画面が続くことを確認する。

管理コンソールで **Clients** → **`device-reservation`** → **Sessions** などを見ると、アクティブセッションが増えている場合があります。

## よくあるつまずき

### ログインボタンを押してもアプリに戻れない／画面が変わらない

0. 上記 **「診断: エクスポート JSON」** を確認する。`publicClient: false` なら **Client authentication を Off** に直す（PKCE だけいじっても解決しない）。
1. **ブラウザの開発者ツール → コンソール** に `[Keycloak` で始まるログや赤いエラーが出ていないか確認する（このリポジトリのフロントは開発モードで Keycloak の詳細ログを有効にしている）。
2. アドレスバーに **`error=`** や **`error_description=`** が付いていないか見る（例: `login_required`, `invalid_redirect_uri`）。付いていればその英語メッセージが原因の手がかり。
3. **Valid redirect URIs** に、実際にアプリが開いているオリジン（`http://localhost:5173` など）が **`/*` 付きで**入っているか再確認する。このフロントはコールバックを **URL のクエリ**（`?code=...&state=...`）で受け取るため、リダイレクト後は一瞬 URL にパラメータが付くのが正常です。

### 「Invalid parameter: redirect_uri」

- **Valid redirect URIs** に、実際にリダイレクトされている URL（オリジン＋パス＋クエリの前方一致）が含まれていない。
- 対処: ブラウザのアドレスバーで失敗時の `redirect_uri=` の値を確認し、同じプレフィックスが `Valid redirect URIs` にあるか確認する。開発では **`http://localhost:5173/*`** を入れておくと安全。

### ブラウザコンソールに CORS エラーが出る

- **Web origins** にフロントのオリジン（例: `http://localhost:5173`）が無い、または `https` / `http` やポートの表記が実際と違う。
- 対処: **Web origins** はスキーム＋ホスト＋ポートまで。パスは付けない。

### ログインはできるがログアウトでエラー

- **Valid post logout redirect URIs** に、ログアウト後の戻り先（このアプリでは **`http://localhost:5173`** 相当）が許可されていない。
- 対処: `http://localhost:5173/*` を追加して Save。

### 管理コンソールに入れない

- Keycloak が起動直後でヘルスチェック前にアクセスしている。数十秒待ってから再読み込み。
- ポート **8080** が別プロセスに占有されている。`compose` のログで Keycloak が Listen しているか確認。

### クライアントを作ったが「Client not found」に近い挙動

- **別レルム**にクライアントを作り、フロントの **`VITE_KEYCLOAK_REALM`** が `master` のまま。
- **Client ID** の綴りと **`VITE_KEYCLOAK_CLIENT_ID`** が一致していない。

## バックエンドとの関係（参考）

- API は `Authorization: Bearer <JWT>` を検証します。トークンの **issuer**（iss）や **JWKS** は Keycloak のレルム設定と一致している必要があります。
- ルートの `.env` にある Keycloak／JWT 関連の URL は、**実際に発行元として使っている Keycloak**（通常は `http://localhost:8080`）とレルム名に合わせてください。詳細は `.env.example` のコメントを参照してください。

## 関連ファイル

| ファイル | 内容 |
|----------|------|
| [frontend/.env.example](../frontend/.env.example) | `VITE_KEYCLOAK_*` の雛形 |
| [frontend/src/auth/keycloak.ts](../frontend/src/auth/keycloak.ts) | `keycloak-js` の初期化（PKCE S256） |
| [compose.dev.yml](../compose.dev.yml) | 開発時の Keycloak 管理ユーザー |

設定を変えたら **フロントの再起動**（Vite は `.env` 変更で再起動が必要な場合があります）を忘れないでください。
