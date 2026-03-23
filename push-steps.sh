#!/usr/bin/env bash
set -euo pipefail

reponame="$(basename "$(dirname "$0")")"
repopath="$(cd "$(dirname "$0")" && pwd)"

BRANCH=${1:-main}
COMMIT_MSG=${2:-"feat(auth): Keycloak MFA Step1/Step2 実装（メールOTP + TOTP）および infra/docs 追加"}

FILES=(
  ".gitignore"
  "infra/docker-compose.yml"
  "infra/docker-compose-totp.yml"
  "infra/keycloak/realm-export.json"
  "infra/keycloak/realm-export-totp.json"
  "infra/keycloak/.env.example"
  "docs/prd/prd.md"
  "docs/design/logs/design-001-mfa.md"
  "docs/adr/adr-001-keycloak-mfa.md"
  "docs/implementation/logs/impl-001-mfa.md"
  "docs/review/logs/2026-03-20_120000_design_mfa-infrastructure.md"
  "CLAUDE.md"
  ".cursor/rules/autonomous_workflow.mdc"
  ".cursor/rules/core_rules.mdc"
)

# 安全チェック: 未追跡 .env の検出
UNTRACKED_ENV=$(git ls-files --others --exclude-standard | grep -E '\.env$' || true)
if [ -n "$UNTRACKED_ENV" ]; then
  echo "ERROR: 未追跡の .env ファイルが存在します。コミット前に必ず確認してください:"
  echo "$UNTRACKED_ENV"
  exit 1
fi

# .env が .gitignore に含まれているか確認
if ! git check-ignore -q .env; then
  echo "WARNING: .env が .gitignore に含まれていません。続行しますか？ (y/N)"
  read -r yn
  case "$yn" in
    [Yy]*) ;;
    *) echo "中止"; exit 1;;
  esac
fi

# ステージ
for f in "${FILES[@]}"; do
  if [ -e "$f" ]; then
    git add "$f"
  else
    echo "Notice: ファイルが見つかりません（スキップ）: $f"
  fi
done

# 差分確認
git status --porcelain

echo "コミットして push しますか？ (y/N)"
read -r confirm
case "$confirm" in
  [Yy]*) ;;
  *) echo "中止"; exit 1;;
esac

git commit -m "$COMMIT_MSG" || { echo "コミットする変更がありません。"; }
git push origin "$BRANCH"

echo "完了: pushed to origin/$BRANCH"
