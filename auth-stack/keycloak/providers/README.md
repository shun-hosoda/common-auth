# このディレクトリについて

Keycloak SPI プロバイダー JAR の格納先です。

**.jar ファイルは .gitignore により追跡されません。**  
`download-providers.ps1` を実行してダウンロードしてください:

```powershell
.\auth-stack\keycloak\providers\download-providers.ps1
```

## 含まれるプロバイダー

| JAR ファイル | バージョン | 用途 |
|------------|---------|------|
| `keycloak-2fa-email-authenticator.jar` | v26.1.1 | Email OTP MFA ([mesutpiskin/keycloak-2fa-email-authenticator](https://github.com/mesutpiskin/keycloak-2fa-email-authenticator)) |

## ⚠️ 本番環境への適用時の注意

- `download-providers.ps1` はダウンロード後に **SHA256 チェックサム検証** を自動実行します。
  検証失敗（不一致）の場合は JAR を自動削除してスクリプトを終了します。
- プロバイダーを更新する際は、**GitHub Releases ページ**で公開されているチェックサムと `$expectedSha` 変数の値を必ず照合してください。
- 本番環境では、サードパーティ SPI の **署名検証**（コード署名証明書）も推奨します。
- JAR の内容を信頼できる環境以外で実行しないでください。
