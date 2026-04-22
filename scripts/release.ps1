#!/usr/bin/env pwsh
# scripts/release.ps1 — common-auth リリーススクリプト
#
# 使い方:
#   .\scripts\release.ps1 -Version 1.0.1
#   .\scripts\release.ps1 -Version 1.1.0 -Message "feat: add invitation expiry"
#
# 前提条件:
#   - git がインストール済みで origin/main にアクセスできること
#   - main ブランチにいること、未コミットの変更がないこと

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [string]$Message = ""
)

$ErrorActionPreference = "Stop"
$tag = "v$Version"

# ── 事前チェック ──────────────────────────────────────────────────────────────
Write-Host "🔍 Pre-flight checks..." -ForegroundColor Cyan

$branch = git rev-parse --abbrev-ref HEAD
if ($branch -ne "main") {
    Write-Error "Must be on main branch. Current: $branch"
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Error "Uncommitted changes detected. Commit or stash them first."
    exit 1
}

$existing = git tag -l $tag
if ($existing) {
    Write-Error "Tag $tag already exists."
    exit 1
}

Write-Host "✅ All checks passed" -ForegroundColor Green

# ── バージョン番号を各パッケージに書き込む ───────────────────────────────────
Write-Host "📦 Updating version to $Version..." -ForegroundColor Cyan

# backend-sdk: pyproject.toml
$pyproject = "packages\backend-sdk\pyproject.toml"
(Get-Content $pyproject) -replace '^version = .*', "version = `"$Version`"" | Set-Content $pyproject

# frontend-sdk: package.json
Push-Location packages\frontend-sdk
npm version $Version --no-git-tag-version | Out-Null
Pop-Location

Write-Host "✅ Versions updated" -ForegroundColor Green

# ── コミット & タグ ───────────────────────────────────────────────────────────
$commitMsg = if ($Message) { "chore: release $tag — $Message" } else { "chore: release $tag" }

git add packages\backend-sdk\pyproject.toml packages\frontend-sdk\package.json
git commit -m $commitMsg
git tag -a $tag -m $commitMsg

Write-Host "🏷️  Created tag $tag" -ForegroundColor Cyan

# ── Push ─────────────────────────────────────────────────────────────────────
git push origin main
git push origin $tag

Write-Host ""
Write-Host "🚀 Released $tag!" -ForegroundColor Green
Write-Host ""
Write-Host "GitHub Actions が以下を自動実行します:"
Write-Host "  • backend-sdk wheel/sdist → GitHub Releases に添付"
Write-Host "  • @common-auth/react → GitHub Packages (npm) に publish"
Write-Host ""
Write-Host "各サービスでのアップデート:"
Write-Host "  Python: requirements.txt の URL を v$Version に更新 → pip install -r requirements.txt"
Write-Host "  npm:    npm install @common-auth/react@$Version"
