# Keycloak SPI プロバイダー JAR ダウンロードスクリプト
# auth-stack 起動前に実行してください

$providersDir = $PSScriptRoot

# mesutspiskin/keycloak-2fa-email-authenticator v26.1.1
$jarUrl      = "https://github.com/mesutpiskin/keycloak-2fa-email-authenticator/releases/download/v26.1.1/keycloak-2fa-email-authenticator-v26.1.1.jar"
$jarPath     = Join-Path $providersDir "keycloak-2fa-email-authenticator.jar"
# GitHub Releases ページで公開されている SHA256 チェックサム（v26.1.1）
$expectedSha = "1944C1B077EB7FBB5B2FC2DC5675D8F4F76AB352D10DB5ABF9F2A7C7021C841D"

if (Test-Path $jarPath) {
    Write-Host "[OK] $($jarPath | Split-Path -Leaf) は既に存在します"
} else {
    Write-Host "ダウンロード中: keycloak-2fa-email-authenticator.jar ..."
    Invoke-WebRequest -Uri $jarUrl -OutFile $jarPath
    Write-Host "[OK] ダウンロード完了: $((Get-Item $jarPath).Length) bytes"
}

# --- SHA256 チェックサム検証 ---
$actualSha = (Get-FileHash $jarPath -Algorithm SHA256).Hash
if ($actualSha -eq $expectedSha) {
    Write-Host "[OK] SHA256 チェックサム一致: $actualSha"
} else {
    Write-Error "[NG] SHA256 不一致！ JAR が改ざんされている可能性があります。`n  期待値: $expectedSha`n  実際値: $actualSha"
    Remove-Item $jarPath -Force
    exit 1
}
