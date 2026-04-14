# 🔥 既知の落とし穴（AIが最初に読むこと）

このプロジェクトで過去に繰り返し発生したバグ一覧。
**症状と一致したら、診断コマンドを実行して即自己解決すること。**

---

## P1: `hasRole('tenant_admin')` が常に false を返す

**症状**: `admin_*@example.com` でログインしても管理画面に遷移できない / SideNav にユーザー管理が表示されない

**根本原因**: Keycloak の `roles` クライアントスコープの `realm roles` マッパーで `id.token.claim` が `false`（未設定）。
`oidc-client-ts` の `user.profile` は IDトークン由来なのでロールが空になる。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$sc = (Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/client-scopes' -Headers @{Authorization="Bearer $t"}) | Where-Object { $_.name -eq 'roles' }
$mp = Invoke-RestMethod -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models" -Headers @{Authorization="Bearer $t"}
$mp | ForEach-Object { "$($_.name): id.token=$($_.config.'id.token.claim')" }
# ✅ 正常: realm roles: id.token=true
# ❌ 異常: realm roles: id.token= (空)
```

**自己修正コマンド**:
```powershell
# 上記の $t, $sc, $mp を取得済みの前提
$rm = $mp | Where-Object { $_.name -eq 'realm roles' }
$rm.config | Add-Member -MemberType NoteProperty -Name 'id.token.claim' -Value 'true' -Force
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models/$($rm.id)" -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body ($rm | ConvertTo-Json -Depth 10)
$cm = $mp | Where-Object { $_.name -eq 'client roles' }
$cm.config | Add-Member -MemberType NoteProperty -Name 'id.token.claim' -Value 'true' -Force
Invoke-RestMethod -Method Put -Uri "http://localhost:8080/admin/realms/common-auth/client-scopes/$($sc.id)/protocol-mappers/models/$($cm.id)" -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body ($cm | ConvertTo-Json -Depth 10)
Write-Host 'Fixed. ブラウザで再ログインしてください。'
```

**恒久対策済み**:
- `auth-stack/keycloak/realm-export.json` の `realm roles` / `client roles` マッパーに `"id.token.claim": "true"` を追加済み
- `packages/frontend-sdk/src/AuthProvider.tsx` の `extractRealmRoles()` がアクセストークンを優先して読むよう修正済み（二重防御）

---

## P2: パスワードリセットメールが届かない

**症状**: Keycloak のパスワードリセットを実行しても MailHog に何も届かない

**根本原因**: `realm-export.json` の SMTP 設定に `"#{SMTP_HOST}"` というリテラル文字列（プレースホルダー未展開）が入っていた。
`docker-compose down -v` + 再起動でこの設定が再インポートされると再発する。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$realm = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth' -Headers @{Authorization="Bearer $t"}
$realm.smtpServer | ConvertTo-Json
# ✅ 正常: "host": "mailhog", "port": "1025"
# ❌ 異常: "host": "#{SMTP_HOST}" または空
```

**自己修正コマンド**:
```powershell
$body = @{smtpServer=@{host='mailhog';port='1025';from='noreply@example.com';fromDisplayName='Common Auth';auth='false';ssl='false';starttls='false'}} | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri 'http://localhost:8080/admin/realms/common-auth' -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body $body
Write-Host 'Fixed. Keycloak再起動不要。'
```

**恒久対策済み**: `auth-stack/keycloak/realm-export.json` の `smtpServer` を `mailhog:1025` に修正済み。

---

## P3: SDK変更がブラウザに反映されない

**症状**: `packages/frontend-sdk/src/` を編集してもブラウザの動作が変わらない

**根本原因**: `npm run dev`（Vite）はローカルパッケージを自動ビルドしない。
かつ `node_modules/.vite` キャッシュが古いビルドを保持する。

**診断確認**:
```powershell
# dist が src より古い = ビルド未実施
Get-Item packages/frontend-sdk/dist/index.mjs | Select-Object LastWriteTime
Get-Item packages/frontend-sdk/src/AuthProvider.tsx | Select-Object LastWriteTime
```

**自己修正コマンド**:
```powershell
Set-Location packages/frontend-sdk; npm run build
Set-Location ../../examples/react-app; Remove-Item -Recurse -Force node_modules/.vite
npm run dev
```

**恒久対策済み**: `examples/react-app/package.json` の `predev` スクリプトが SDK ビルド + Vite キャッシュクリアを自動実行。
`npm run dev` 1コマンドで常に最新状態が起動する。

---

## P4: Keycloak ログイン失敗時に HTTP 500（error ID表示）

**症状**: 誤ったパスワード入力などでログインが失敗すると、エラーメッセージでなく `Error ID xxxxxxxx` が表示される

**根本原因**: カスタムテーマの `theme.properties` に `import=common` があると
`FreeMarkerLoginFormsProvider.createErrorPage` で `ArrayIndexOutOfBoundsException` が発生する。

**診断確認**:
```powershell
Get-Content auth-stack/keycloak/themes/common-auth/login/theme.properties
# ❌ 異常: import=common が存在する
# ✅ 正常: import=common が存在しない
```

**自己修正**: `auth-stack/keycloak/themes/common-auth/login/theme.properties` から `import=common` 行を削除し、Keycloakコンテナのみ再起動（ボリューム削除不要）:
```powershell
docker restart common-auth-keycloak
```

**恒久対策済み**: `theme.properties` から `import=common` を削除済み。

---

## P5: Docker ヘルスチェックが `unhealthy` と表示される（Windows）

**症状**: `docker ps` で Keycloak が `unhealthy` と表示されるが、実際には起動している

**根本原因**: Windows の Docker Desktop ではシェル互換性の問題でヘルスチェックコマンドが失敗する。偽陽性。

**確認コマンド**:
```powershell
Invoke-WebRequest -Uri http://localhost:8080/health/ready -UseBasicParsing | Select-Object StatusCode
# 200 なら正常稼働中（unhealthy 表示は無視してよい）
```

---

## P6: ユーザー管理画面（Admin API）が動作しない

**症状**: React の管理画面でユーザー一覧が表示されない / ネットワークタブで `/api/admin/users` が 401・403・404・500 を返す

**根本原因**: 複数の設定不備が連鎖的に発生する。

| 段階 | エラー | 原因 |
|------|--------|------|
| 404 | `/api/admin/users` が見つからない | `setup.py` の admin router prefix と Vite proxy パスの不一致 |
| 401 | `Audience doesn't match` | `KEYCLOAK_CLIENT_ID` が `backend-app` のままで `example-app` と不一致 / audience mapper 未設定 |
| 500 | `Admin API not configured (KC_ADMIN_CLIENT_SECRET missing)` | `admin-api-client` が Keycloak に未作成 / `.env` に `KC_ADMIN_*` 未設定 / `load_dotenv()` 未呼出 |
| 403 | Keycloak Admin API が Forbidden | `admin-api-client` の `defaultClientScopes` に `roles` が含まれていない |

**診断コマンド**:
```powershell
# 1. Admin router のパスが正しいか
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/common-auth/protocol/openid-connect/token' -Body @{grant_type='password';client_id='example-app';username='admin_acme-corp@example.com';password='admin123'}).access_token
Invoke-RestMethod -Uri 'http://localhost:8000/api/admin/users' -Headers @{Authorization="Bearer $t"} -Method Get
# ✅ 正常: ユーザー一覧 JSON が返る
# ❌ 異常: 404/401/403/500

# 2. audience mapper が設定されているか
$at = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$clients = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/clients' -Headers @{Authorization="Bearer $at"}
$ea = $clients | Where-Object { $_.clientId -eq 'example-app' }
$mappers = Invoke-RestMethod -Uri "http://localhost:8080/admin/realms/common-auth/clients/$($ea.id)/protocol-mappers/models" -Headers @{Authorization="Bearer $at"}
$mappers | Where-Object { $_.protocolMapper -eq 'oidc-audience-mapper' } | Select-Object name
# ✅ 正常: audience-mapper が存在する
# ❌ 異常: 空

# 3. admin-api-client が存在し、roles スコープを持つか
$aac = $clients | Where-Object { $_.clientId -eq 'admin-api-client' }
if ($aac) { Write-Host "admin-api-client exists: $($aac.id)" } else { Write-Host "❌ admin-api-client not found" }

# 4. .env に KC_ADMIN_* が設定されているか
Get-Content examples/fastapi-app/.env | Select-String "KC_ADMIN"
# ✅ 正常: KC_ADMIN_CLIENT_ID=admin-api-client, KC_ADMIN_CLIENT_SECRET=<secret>
```

**恒久対策済み**:
- `setup.py`: admin router prefix を `/api/admin` に修正済み
- `realm-export.json`: `example-app` に `oidc-audience-mapper` 追加済み
- `realm-export.json`: `admin-api-client`（confidential, `roles` スコープ付き, `realm-admin` サービスアカウントロール）追加済み
- `main.py`: `load_dotenv()` を追加して `os.environ.get("KC_ADMIN_*")` が `.env` を読むよう修正済み
- `.env.example`: `KC_ADMIN_CLIENT_ID` / `KC_ADMIN_CLIENT_SECRET` テンプレート追加済み

---

## P7: MFA有効なのにOTPが表示されない（CONDITIONAL subflowスキップ）

**症状**: テナントMFAを有効化しOTPを登録済みなのに、ログイン時にOTPを聞かれずダッシュボードに遷移する

**根本原因**: `realm-export.json` の `authenticatorConfig` で `conditional-user-attribute` の設定キー名が誤っていた。
Keycloak 24 の正しいキー名は `attribute_expected_value` だが、`expected_attribute_value` と記述されていた。
条件プロバイダーが比較値を読めず常に FALSE を返すため、CONDITIONAL subflow 全体がスキップされていた。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$execs = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/authentication/flows/unified-mfa-browser%20mfa-gate/executions' -Headers @{Authorization="Bearer $t"}
foreach ($e in $execs) {
    if ($e.authenticationConfig) {
        $cfg = Invoke-RestMethod -Uri "http://localhost:8080/admin/realms/common-auth/authentication/config/$($e.authenticationConfig)" -Headers @{Authorization="Bearer $t"}
        Write-Host "$($cfg.alias): $($cfg.config | ConvertTo-Json -Compress)"
    }
}
# ✅ 正常: "attribute_expected_value":"true" (attribute_ で始まる)
# ❌ 異常: "expected_attribute_value":"true" (expected_ で始まる)
```

**自己修正コマンド**:
```powershell
# config IDを取得して正しいキー名で更新
$configs = @(
    @{id=$execs[0].authenticationConfig; alias='mfa-gate-condition'; config=@{attribute_name='mfa_enabled'; attribute_expected_value='true'; not='false'}},
    @{id=$execs[1].authenticationConfig; alias='mfa-method-totp'; config=@{attribute_name='mfa_method'; attribute_expected_value='totp'; not='false'}}
)
foreach ($c in $configs) {
    Invoke-RestMethod -Method Put -Uri "http://localhost:8080/admin/realms/common-auth/authentication/config/$($c.id)" -Headers @{Authorization="Bearer $t"; 'Content-Type'='application/json'} -Body ($c | ConvertTo-Json -Depth 5)
}
Write-Host 'Fixed. ブラウザで再ログインしてください。'
```

**恒久対策済み**: `auth-stack/keycloak/realm-export.json` の設定キーを `attribute_expected_value` に修正済み。

---

## P8: JSX `{condition && (...)}` 内への複数要素追加でコンパイルエラー

**症状**: `npm run dev` 起動時に esbuild が `Expected ")" but found "{"` を出力してサーバーが起動しない

**根本原因**: JSX 式 `{condition && (...)}` の括弧内には単一の式しか置けない。
既存ブロックの後ろに新しい `<div>` を追加すると、`&&` の右辺が複数要素になり構文エラーになる。

**診断確認**:
```powershell
npx tsc --noEmit -p examples/react-app/tsconfig.json
# ❌ 異常: JSX expressions must have one parent element など
# ✅ 正常: エラーなし（0 件）
```

**自己修正**: 複数要素を `<>...</>` Fragment でラップする。

```tsx
{/* 修正前（エラー）*/}
{!loading && (
  <div>...</div>
  <div>...</div>   // ← 2つ目が構文エラー
)}

{/* 修正後 */}
{!loading && (
  <>
    <div>...</div>
    <div>...</div>
  </>
)}
```

**AI レビュー時の必須確認**: `.tsx`/`.jsx` ファイルに要素追加を行う場合、
diff だけでなく **変更箇所の前後 30 行以上を読み、囲んでいる JSX 式（`&&`・三項・`return`）が単一ルートかどうかを確認すること**。
確認後に `tsc --noEmit` を実行してコンパイルエラーがないことを検証すること。

---

## P9: MFA有効化しても次回ログインでOTPが要求されない（User Profile unmanaged attributes）

**症状**: セキュリティ設定画面でMFAを有効化し、Keycloak Account ConsoleでTOTP設定済みなのに、次回ログイン時にOTP入力画面が表示されない。 `/api/auth/mfa-status` の応答で `mfa_enabled: false` が返る。

**根本原因**: Keycloak 24 の User Profile 機能で `unmanagedAttributePolicy` が未設定（デフォルト = DISABLED）。
`admin-api-client` のサービスアカウント経由で `mfa_enabled` / `mfa_method` 等のカスタム属性を書き込んでも、
User Profile が「未定義属性」としてサイレントに無視するため、属性が永続化されない。
結果として `conditional-user-attribute` 認証プロバイダーが `mfa_enabled=true` を読めず、MFA subflow がスキップされる。

> 注意: `admin-cli`（master realm）は User Profile 制限をバイパスするため、Keycloak管理コンソールでは属性が見える。
> しかし `admin-api-client`（realm-level service account）からの操作は User Profile ポリシーに従う。

**診断コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$upConfig = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/users/profile' -Headers @{Authorization="Bearer $t"}
Write-Host "unmanagedAttributePolicy: $($upConfig.unmanagedAttributePolicy)"
# ✅ 正常: ADMIN_EDIT
# ❌ 異常: (空) または DISABLED
```

**自己修正コマンド**:
```powershell
$t = (Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/realms/master/protocol/openid-connect/token' -Body @{grant_type='password';client_id='admin-cli';username='admin';password='admin'}).access_token
$upConfig = Invoke-RestMethod -Uri 'http://localhost:8080/admin/realms/common-auth/users/profile' -Headers @{Authorization="Bearer $t"}
$upConfig | Add-Member -MemberType NoteProperty -Name 'unmanagedAttributePolicy' -Value 'ADMIN_EDIT' -Force
Invoke-RestMethod -Method Put -Uri 'http://localhost:8080/admin/realms/common-auth/users/profile' -Headers @{Authorization="Bearer $t";'Content-Type'='application/json'} -Body ($upConfig | ConvertTo-Json -Depth 20)
Write-Host 'Fixed. MFAの有効化/無効化を再実行してください。'
```

**修正後の属性再ミラー**: User Profile 修正後、既存ユーザーに属性が反映されていない場合は、
セキュリティ設定画面から MFA を再度有効化（PUT /api/admin/security/mfa）すること。
これにより `set_user_attributes_bulk` が全テナントユーザーに `mfa_enabled`/`mfa_method` を再設定する。

**恒久対策済み**: `auth-stack/keycloak/realm-export.json` に `components` セクションを追加し、
`org.keycloak.userprofile.UserProfileProvider` の `unmanagedAttributePolicy: "ADMIN_EDIT"` を設定済み。
