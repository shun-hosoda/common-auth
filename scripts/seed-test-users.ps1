# テストユーザー一括作成スクリプト
# Keycloak Admin API を使用して以下を作成します：
#   - super_admin@example.com  (super_admin ロール)
#   - user001_acme-corp@example.com ～ user100_acme-corp@example.com
#   - user001_globex-inc@example.com ～ user100_globex-inc@example.com
#
# 使い方:
#   .\scripts\seed-test-users.ps1
#   .\scripts\seed-test-users.ps1 -KeycloakUrl http://localhost:8080 -AdminPassword admin

param(
    [string]$KeycloakUrl    = "http://localhost:8080",
    [string]$Realm          = "common-auth",
    [string]$AdminUser      = "admin",
    [string]$AdminPassword  = "admin",
    [int]   $UsersPerTenant = 100
)

$ErrorActionPreference  = "Stop"
$ProgressPreference     = "SilentlyContinue"   # Invoke-RestMethod の進捗バーを非表示

# ── 管理者トークン取得 ────────────────────────────────────────────────────────
function Get-AdminToken {
    $body = @{
        grant_type = "password"
        client_id  = "admin-cli"
        username   = $AdminUser
        password   = $AdminPassword
    }
    $resp = Invoke-RestMethod `
        -Method Post `
        -Uri "$KeycloakUrl/realms/master/protocol/openid-connect/token" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body $body
    return $resp.access_token
}

# ── ユーザー作成 ──────────────────────────────────────────────────────────────
function New-KcUser {
    param(
        [string]$Token,
        [hashtable]$Payload
    )
    $headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
    $uri = "$KeycloakUrl/admin/realms/$Realm/users"
    try {
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
            -Body ($Payload | ConvertTo-Json -Depth 10) -ErrorAction Stop | Out-Null
        return $true
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 409) { return "exists" }
        Write-Warning "  Error ($statusCode): $_"
        return $false
    }
}

# ── ユーザー検索 (username) ───────────────────────────────────────────────────
function Get-KcUserId {
    param([string]$Token, [string]$Username)
    $headers = @{ Authorization = "Bearer $Token" }
    $uri = "$KeycloakUrl/admin/realms/$Realm/users?username=$([uri]::EscapeDataString($Username))&exact=true"
    $users = Invoke-RestMethod -Uri $uri -Headers $headers
    return ($users | Select-Object -First 1).id
}

# ── ロール付与 ────────────────────────────────────────────────────────────────
function Add-RealmRole {
    param([string]$Token, [string]$UserId, [string]$RoleName)
    $headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }

    # ロール情報取得
    $role = Invoke-RestMethod `
        -Uri "$KeycloakUrl/admin/realms/$Realm/roles/$([uri]::EscapeDataString($RoleName))" `
        -Headers @{ Authorization = "Bearer $Token" }

    Invoke-RestMethod -Method Post `
        -Uri "$KeycloakUrl/admin/realms/$Realm/users/$UserId/role-mappings/realm" `
        -Headers $headers `
        -Body (ConvertTo-Json @($role)) | Out-Null
}

# ── グループ追加 ──────────────────────────────────────────────────────────────
function Add-UserToGroup {
    param([string]$Token, [string]$UserId, [string]$TenantId)
    $headers = @{ Authorization = "Bearer $Token" }

    # /tenants/<tenantId> グループを検索
    $groups = Invoke-RestMethod -Uri "$KeycloakUrl/admin/realms/$Realm/groups?search=tenants" -Headers $headers
    $tenants = $groups | Where-Object { $_.name -eq "tenants" } | Select-Object -First 1
    if (-not $tenants) { Write-Warning "  'tenants' group not found"; return }

    $subgroups = Invoke-RestMethod -Uri "$KeycloakUrl/admin/realms/$Realm/groups/$($tenants.id)/children" -Headers $headers
    $target = $subgroups | Where-Object { $_.name -eq $TenantId } | Select-Object -First 1
    if (-not $target) { Write-Warning "  subgroup '$TenantId' not found"; return }

    $putHeaders = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
    Invoke-RestMethod -Method Put `
        -Uri "$KeycloakUrl/admin/realms/$Realm/users/$UserId/groups/$($target.id)" `
        -Headers $putHeaders | Out-Null
}

# ════════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=== Keycloak テストユーザー一括作成 ===" -ForegroundColor Cyan
Write-Host "  KeycloakUrl : $KeycloakUrl"
Write-Host "  Realm       : $Realm"
Write-Host "  UsersPerTenant: $UsersPerTenant"
Write-Host ""

Write-Host "[1/4] Admin トークン取得中..." -ForegroundColor Yellow
$token = Get-AdminToken
Write-Host "  OK"

# ── super_admin 作成 ─────────────────────────────────────────────────────────
Write-Host "[2/4] super_admin@example.com 作成中..." -ForegroundColor Yellow
$payload = @{
    username      = "super_admin@example.com"
    email         = "super_admin@example.com"
    emailVerified = $true
    enabled       = $true
    firstName     = "Super"
    lastName      = "Admin"
    attributes    = @{}
    credentials   = @(@{ type = "password"; value = "superadmin123"; temporary = $false })
}
$result = New-KcUser -Token $token -Payload $payload
if ($result -eq $true) {
    $uid = Get-KcUserId -Token $token -Username "super_admin@example.com"
    Add-RealmRole -Token $token -UserId $uid -RoleName "user"
    Add-RealmRole -Token $token -UserId $uid -RoleName "super_admin"
    Write-Host "  作成済み (id=$uid)" -ForegroundColor Green
} elseif ($result -eq "exists") {
    Write-Host "  既に存在します（スキップ）" -ForegroundColor DarkYellow
} else {
    Write-Host "  作成失敗" -ForegroundColor Red
}

# ── テナントごとに100ユーザー作成 ─────────────────────────────────────────────
$tenants = @("acme-corp", "globex-inc")

$step = 3
foreach ($tenantId in $tenants) {
    Write-Host "[$step/4] $tenantId のテストユーザー $UsersPerTenant 件作成中..." -ForegroundColor Yellow
    $created = 0; $skipped = 0; $failed = 0

    for ($i = 1; $i -le $UsersPerTenant; $i++) {
        $num      = $i.ToString("000")
        $username = "user${num}_${tenantId}@example.com"
        $payload  = @{
            username      = $username
            email         = $username
            emailVerified = $true
            enabled       = $true
            firstName     = "User$num"
            lastName      = $tenantId
            attributes    = @{ tenant_id = @($tenantId) }
            credentials   = @(@{ type = "password"; value = "password123"; temporary = $false })
        }
        $result = New-KcUser -Token $token -Payload $payload
        if ($result -eq $true) {
            $uid = Get-KcUserId -Token $token -Username $username
            Add-RealmRole -Token $token -UserId $uid -RoleName "user"
            Add-UserToGroup -Token $token -UserId $uid -TenantId $tenantId
            $created++
        } elseif ($result -eq "exists") {
            $skipped++
        } else {
            $failed++
        }

        # 進捗表示（10件ごと）
        if ($i % 10 -eq 0) {
            Write-Host "  ... $i / $UsersPerTenant 件処理済み (作成:$created, スキップ:$skipped, 失敗:$failed)"
        }
    }
    Write-Host "  完了: 作成=$created, スキップ=$skipped, 失敗=$failed" -ForegroundColor Green
    $step++
}

Write-Host ""
Write-Host "=== 完了 ===" -ForegroundColor Cyan
Write-Host "テストユーザー一覧: docs/test-users.md"
Write-Host ""
