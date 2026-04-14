# 起動前セルフチェックリスト

作業開始時に以下を確認すること:

```
[ ] docker ps → 4コンテナ(keycloak, keycloak-db, app-db, mailhog)が起動中
[ ] curl http://localhost:8080/health/ready → HTTP 200
[ ] http://localhost:8025 → MailHog UI 表示
[ ] realm roles マッパーの id.token.claim = true (P1診断コマンドで確認)
[ ] SMTP host = mailhog (P2診断コマンドで確認)
[ ] examples/fastapi-app/.env が存在する（KC_ADMIN_* 含む）
[ ] examples/react-app/.env が存在する
[ ] GET /api/admin/users が 200 を返す (P6診断コマンドで確認)
[ ] npx tsc --noEmit -p examples/react-app/tsconfig.json → エラーなし (P8参照)
[ ] User Profile unmanagedAttributePolicy = ADMIN_EDIT (P9診断コマンドで確認)
```

`docker-compose down -v` 後に再起動した場合は **P1・P2・P6・P9 を必ず再診断すること**。

## クイック起動手順

```powershell
# 1. Docker 起動
cd auth-stack
docker-compose up -d

# 2. Keycloak 起動待ち（30-60秒）
do { Start-Sleep 5; $r = try { Invoke-WebRequest -Uri http://localhost:8080/health/ready -UseBasicParsing } catch { $null } } while ($r.StatusCode -ne 200)

# 3. Backend 起動
cd ../examples/fastapi-app
uvicorn main:app --reload --port 8000

# 4. Frontend 起動（別ターミナル）
cd examples/react-app
npm run dev
```
