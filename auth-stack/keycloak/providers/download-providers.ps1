# Keycloak SPI プロバイダー JAR 検証スクリプト
# auth-stack 起動前に実行してください
#
# JAR はリポジトリに同梱済み（v26.3.0, main ブランチからビルド）。
# skipSetup=true 対応版。GitHub リリースに v26.3.0 が公開された場合は
# そちらからダウンロードするよう変更してください。
#
# ビルド元: https://github.com/mesutpiskin/keycloak-2fa-email-authenticator (main)

$providersDir = $PSScriptRoot
$jarPath     = Join-Path $providersDir "keycloak-2fa-email-authenticator.jar"
# v26.3.0 (built from main, includes skipSetup feature)
$expectedSha = "B28F584E925317737E5BBA7F7FF8F6EA597629E3361DE44C2AFF50921FC882E2"

if (-not (Test-Path $jarPath)) {
    Write-Error "[NG] $($jarPath | Split-Path -Leaf) が見つかりません。リポジトリから取得してください。"
    exit 1
}

# --- SHA256 チェックサム検証 ---
$actualSha = (Get-FileHash $jarPath -Algorithm SHA256).Hash
if ($actualSha -eq $expectedSha) {
    Write-Host "[OK] SHA256 チェックサム一致: $actualSha"
} else {
    Write-Error "[NG] SHA256 不一致！ JAR が改ざんされている可能性があります。`n  期待値: $expectedSha`n  実際値: $actualSha"
    exit 1
}
