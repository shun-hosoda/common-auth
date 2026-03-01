# ADR-009: Email送信方式の選定

## ステータス

承認

## コンテキスト

Phase 2で以下の機能を実装する際、Email送信が必要になる:
- **FR-011**: パスワードリセット（リセットリンク付きメール）
- **FR-012**: ユーザーセルフ登録（メールアドレス確認）
- **FR-010**: MFA設定（オプションでバックアップコード送信）

Email送信の実装方式には複数の選択肢がある:
1. Keycloak内蔵のSMTP機能
2. 外部Email API（SendGrid, AWS SES, Mailgun等）
3. 自前SMTPサーバー

### 要件
- **ポータビリティ**: AWS/Azure/GCP/オンプレミスを問わず動作
- **設定の簡素化**: `.env`ファイルで設定完結
- **セキュリティ**: SMTP認証情報の安全な管理
- **運用コスト**: 追加インフラを最小限に
- **将来性**: 大規模運用時のスケーラビリティ

## 決定

**Keycloak内蔵SMTP機能**を使用する。

### 設定方法

Keycloak Realm設定に以下を追加:

```json
{
  "smtpServer": {
    "host": "#{SMTP_HOST}",
    "port": "#{SMTP_PORT}",
    "from": "#{SMTP_FROM}",
    "fromDisplayName": "Common Auth Platform",
    "replyTo": "#{SMTP_FROM}",
    "auth": "true",
    "user": "#{SMTP_USER}",
    "password": "#{SMTP_PASSWORD}",
    "starttls": "true",
    "ssl": "false"
  }
}
```

**環境変数** (`.env`):
```bash
# SMTP Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=noreply@example.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Keycloak環境変数置換**: Keycloak 24.0以降は`#{VAR_NAME}`形式で環境変数を参照できる。

## 選択肢

### 選択肢A: Keycloak内蔵SMTP（採用）

- **メリット**: 
  - **ポータビリティ**: 外部サービス依存なし、Dockerコンテナのみで完結
  - **設定の簡素化**: `.env`で環境変数設定のみ、追加インフラ不要
  - **コスト**: 無料（既存のSMTPサーバーを使用）
  - **統合が容易**: Keycloakが自動的にメール送信タイミングを管理
  - **テンプレート管理**: Keycloak Themeでメールテンプレートをカスタマイズ可能
- **デメリット**: 
  - **送信レート制限**: 多くのSMTPサーバーには送信レート制限がある（例: Gmail 500通/日）
  - **到達率**: 外部Email APIと比較して到達率が低い可能性（SPF/DKIM設定が重要）
  - **スケーラビリティ**: 大規模運用時（1万通/日以上）は外部APIへの移行が必要

### 選択肢B: 外部Email API（SendGrid, AWS SES等）

- **メリット**: 
  - **高到達率**: SPF/DKIM/DMARC設定が容易、配信レポート機能
  - **高い送信レート**: 数万〜数百万通/日のスケール
  - **高度な機能**: トラッキング、A/Bテスト、テンプレート管理
  - **専門サポート**: 配信トラブル時のサポート
- **デメリット**: 
  - **クラウド依存**: 特定サービスへの依存が発生（ポータビリティ低下）
  - **コスト**: 無料枠を超えると課金（例: SendGrid $15/月〜）
  - **追加設定**: APIキー管理、Webhook設定等の追加作業
  - **複雑化**: Keycloakとの統合に追加実装が必要（Custom Provider）

### 選択肢C: 自前SMTPサーバー

- **メリット**: 
  - **完全コントロール**: すべての設定を自由に管理
  - **コスト**: ランニングコストなし（インフラコストのみ）
- **デメリット**: 
  - **運用負荷**: SMTPサーバーの構築・運用・監視が必要
  - **セキュリティリスク**: スパムリレーや不正利用のリスク
  - **到達率**: IPレピュテーション管理が困難
  - **専門知識**: Postfix/Exim等の深い知識が必要

## 結果

### 実装への影響

#### 1. Auth Stack設定

**`auth-stack/.env.example`** に追加:
```bash
# ===================================
# SMTP Settings (Phase 2)
# ===================================
# Email送信設定（パスワードリセット、メール確認用）
# 本番環境ではシークレット管理ツール（AWS Secrets Manager, Vault等）の使用を推奨
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=noreply@example.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Gmail使用時の注意:
# 1. Googleアカウントで「2段階認証」を有効化
# 2. 「アプリパスワード」を生成して上記SMTP_PASSWORDに設定
# 3. 参考: https://support.google.com/accounts/answer/185833

# その他のSMTPプロバイダ例:
# - Office 365: smtp.office365.com (Port 587)
# - Outlook.com: smtp-mail.outlook.com (Port 587)
# - Yahoo Mail: smtp.mail.yahoo.com (Port 587)
```

**`auth-stack/keycloak/realm-export.json`** に追加:
```json
{
  "smtpServer": {
    "host": "#{SMTP_HOST}",
    "port": "#{SMTP_PORT}",
    "from": "#{SMTP_FROM}",
    "fromDisplayName": "Common Auth Platform",
    "replyTo": "#{SMTP_FROM}",
    "auth": "true",
    "user": "#{SMTP_USER}",
    "password": "#{SMTP_PASSWORD}",
    "starttls": "true"
  }
}
```

**`auth-stack/docker-compose.yml`** に環境変数追加:
```yaml
services:
  keycloak:
    environment:
      # ... existing vars ...
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_FROM=${SMTP_FROM}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
```

#### 2. ドキュメント更新

**`auth-stack/README.md`** に追加セクション:

```markdown
## SMTP設定

Email送信（パスワードリセット、メール確認）にはSMTP設定が必要です。

### Gmail使用例

1. Googleアカウントで2段階認証を有効化
2. [アプリパスワード](https://myaccount.google.com/apppasswords)を生成
3. `.env`に設定:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_FROM=noreply@example.com
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=<generated-app-password>
   ```

### 本番環境でのセキュリティ対策

`.env`にSMTPパスワードを平文保存するのは開発環境のみとしてください。
本番環境では以下のシークレット管理ツールを使用することを推奨します:

- **AWS**: Secrets Manager または Parameter Store
- **Azure**: Key Vault
- **GCP**: Secret Manager
- **汎用**: HashiCorp Vault
- **Docker**: Docker Secrets機能

例（Docker Secrets）:
```bash
echo "smtp-password-value" | docker secret create smtp_password -
```

`docker-compose.yml`:
```yaml
services:
  keycloak:
    secrets:
      - smtp_password
    environment:
      SMTP_PASSWORD_FILE: /run/secrets/smtp_password
```
```

### トレードオフ

#### メリット
- **ポータビリティ最優先**: Dockerコンテナのみで動作、クラウド非依存
- **シンプルな設定**: `.env`ファイルだけで完結
- **コスト効率**: 既存の企業SMTPサーバーやGmail等を無料で利用可能
- **迅速な導入**: 追加インフラ構築不要

#### デメリット・対策

**1. 送信レート制限**
- **問題**: Gmailは500通/日、多くのSMTPサーバーには制限がある
- **対策**: 
  - Phase 1では問題なし（小規模ユーザー想定）
  - Phase 3で外部API対応を検討（SendGrid, SES等）
  - Keycloak Custom Provider実装で切り替え可能

**2. 到達率**
- **問題**: SPF/DKIM設定が不適切だと迷惑メール判定される可能性
- **対策**:
  - ドキュメントにSPF/DKIM設定ガイドを記載
  - 送信元ドメインの信頼性確保（専用ドメイン推奨）

**3. セキュリティ（SMTP認証情報）**
- **問題**: `.env`にパスワードを平文保存するリスク
- **対策**:
  - `.env.example`にセキュリティ警告を明記
  - READMEに本番環境でのシークレット管理ツール使用を推奨
  - `.gitignore`に`.env`を追加（誤コミット防止）

**4. 監視・トラブルシューティング**
- **問題**: 外部APIと異なり、配信レポートやトラッキング機能がない
- **対策**:
  - Keycloakログでメール送信試行を記録
  - SMTPサーバーのログ確認手順をドキュメント化

### 将来の拡張性

Phase 3以降で以下を検討:

1. **外部Email API対応**:
   - Keycloak Custom Email Provider実装
   - SendGrid/AWS SES/Mailgun等への切り替えオプション
   - 設定で切り替え可能に（`EMAIL_PROVIDER=smtp|sendgrid|ses`）

2. **メールテンプレート管理**:
   - Keycloak Theme機能でHTMLテンプレートをカスタマイズ
   - 多言語対応

3. **送信レート管理**:
   - キューイング機能（Redis Queue）
   - バックグラウンドワーカーで非同期送信

## セキュリティ考慮事項

### SMTP認証情報の保護

1. **開発環境**: `.env`使用（ただし`.gitignore`で除外）
2. **本番環境**: 以下のいずれかを使用
   - AWS Secrets Manager / Parameter Store
   - Azure Key Vault
   - GCP Secret Manager
   - HashiCorp Vault
   - Docker Secrets

#### Docker Secrets実装例

**シークレット作成**:
```bash
# SMTPパスワードをシークレットとして作成
echo "your-smtp-password" | docker secret create smtp_password -

# または、ファイルから
echo "your-smtp-password" > smtp_password.txt
docker secret create smtp_password smtp_password.txt
rm smtp_password.txt  # 作成後すぐ削除
```

**docker-compose.prod.yml**:
```yaml
version: '3.8'

services:
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    command: start
    secrets:
      - smtp_password
    environment:
      # 既存の環境変数
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN}
      KC_DB: postgres
      KC_DB_URL: ${KC_DB_URL}
      
      # SMTP設定（パスワード以外）
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_FROM: ${SMTP_FROM}
      SMTP_USER: ${SMTP_USER}
      
      # Docker Secretsを使用（ファイルパス指定）
      SMTP_PASSWORD_FILE: /run/secrets/smtp_password
    ports:
      - "8080:8080"
    networks:
      - auth-network

secrets:
  smtp_password:
    external: true  # 既存のシークレットを参照

networks:
  auth-network:
    driver: bridge
```

**Keycloak起動スクリプト調整**:
```bash
#!/bin/bash
# entrypoint-wrapper.sh

# Docker Secretsからパスワード読み込み
if [ -f /run/secrets/smtp_password ]; then
  export SMTP_PASSWORD=$(cat /run/secrets/smtp_password)
fi

# Keycloak起動
exec /opt/keycloak/bin/kc.sh "$@"
```

**Dockerfile調整** (カスタムイメージ使用の場合):
```dockerfile
FROM quay.io/keycloak/keycloak:24.0

COPY entrypoint-wrapper.sh /opt/keycloak/bin/
RUN chmod +x /opt/keycloak/bin/entrypoint-wrapper.sh

ENTRYPOINT ["/opt/keycloak/bin/entrypoint-wrapper.sh"]
CMD ["start"]
```

**デプロイ**:
```bash
# Docker Swarm mode
docker stack deploy -c docker-compose.prod.yml auth-stack

# Docker Compose（Swarm不使用の場合、ファイル直接マウント）
docker-compose -f docker-compose.prod.yml up -d
```

#### AWS Secrets Manager連携例

```bash
# AWS CLIでシークレット取得
aws secretsmanager get-secret-value \
  --secret-id prod/common-auth/smtp-password \
  --query SecretString \
  --output text
```

**docker-compose.yml with AWS Secrets**:
```yaml
services:
  keycloak:
    environment:
      SMTP_PASSWORD: ${SMTP_PASSWORD}  # 起動前にAWS Secretsから取得して設定
```

**起動スクリプト**:
```bash
#!/bin/bash
# start-with-secrets.sh

# AWS Secrets Managerからパスワード取得
export SMTP_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id prod/common-auth/smtp-password \
  --query SecretString \
  --output text)

# Docker Compose起動
docker-compose up -d
```

### SPF/DKIM設定

Email到達率向上のため、送信元ドメインに以下を設定:

**SPF Record** (DNS TXTレコード):
```
v=spf1 include:_spf.google.com ~all
```

**DKIM**: Gmailの場合は自動設定、独自ドメインの場合は別途設定が必要

### トランスポートセキュリティ

- **STARTTLS**: 推奨（Port 587）
- **SSL/TLS**: 代替（Port 465）
- **平文**: 禁止（Port 25は使用しない）

## 参考

- [Keycloak - Email Settings Documentation](https://www.keycloak.org/docs/latest/server_admin/#_email)
- [Gmail SMTP Settings](https://support.google.com/a/answer/176600)
- [RFC 5321 - SMTP](https://datatracker.ietf.org/doc/html/rfc5321)
- [RFC 7208 - SPF (Sender Policy Framework)](https://datatracker.ietf.org/doc/html/rfc7208)
- [RFC 6376 - DKIM (DomainKeys Identified Mail)](https://datatracker.ietf.org/doc/html/rfc6376)
- [OWASP - Secure Email Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Email_Security_Cheat_Sheet.html)
