<#
.SYNOPSIS
    Smoke test — verifies that all API endpoints respond correctly
    on a running local stack (Keycloak + FastAPI + Vite).

.DESCRIPTION
    This script is the last gate before /push. It:
    1. Checks Docker containers are running
    2. Checks backend health
    3. Obtains an admin JWT
    4. Calls every API endpoint the frontend depends on
    5. Reports PASS/FAIL per endpoint

    Run this AFTER starting docker compose + backend + frontend.

.EXAMPLE
    .\scripts\smoke-test.ps1
    .\scripts\smoke-test.ps1 -BackendPort 8001

.NOTES
    Exit code 0 = all passed, 1 = one or more failures.

    ⚠️  WARNING: This script is for LOCAL DEVELOPMENT ONLY.
    Do NOT run against production or staging environments.
    Credentials in -Username / -Password are test-only defaults.
#>

param(
    [int]$BackendPort = 8000,
    [string]$KeycloakUrl = "http://localhost:8080",
    [string]$Realm = "common-auth",
    [string]$ClientId = "example-app",
    [string]$Username = "admin_acme-corp@example.com",
    [string]$Password = "admin123"
)

$ErrorActionPreference = "Continue"
$pass = 0
$fail = 0
$results = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [string]$Body = $null,
        [int[]]$ExpectedStatus = @(200)
    )

    try {
        $params = @{
            Method = $Method
            Uri = $Url
            Headers = $Headers
            UseBasicParsing = $true
        }
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        $resp = Invoke-WebRequest @params
        $status = $resp.StatusCode

        if ($ExpectedStatus -contains $status) {
            $script:pass++
            $script:results += [PSCustomObject]@{ Test=$Name; Status="PASS"; Code=$status }
        } else {
            $script:fail++
            $script:results += [PSCustomObject]@{ Test=$Name; Status="FAIL"; Code="$status (expected $($ExpectedStatus -join '/'))" }
        }
    } catch {
        $code = "N/A"
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        $script:fail++
        $script:results += [PSCustomObject]@{ Test=$Name; Status="FAIL"; Code="$code - $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" }
    }
}

Write-Host "`n=== Common Auth Smoke Test ===" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:$BackendPort"
Write-Host "Keycloak: $KeycloakUrl"
Write-Host ""

# ── 0. Prerequisites ──────────────────────────────────────────────────────────

Write-Host "[0] Checking prerequisites..." -ForegroundColor Yellow

# Keycloak health
Test-Endpoint -Name "Keycloak health" -Method GET `
    -Url "$KeycloakUrl/health/ready"

# Backend health
Test-Endpoint -Name "Backend health" -Method GET `
    -Url "http://localhost:$BackendPort/auth/health"

# ── 1. Get admin JWT ──────────────────────────────────────────────────────────

Write-Host "[1] Obtaining admin JWT..." -ForegroundColor Yellow

$token = $null
try {
    $tokenResp = Invoke-RestMethod -Method Post `
        -Uri "$KeycloakUrl/realms/$Realm/protocol/openid-connect/token" `
        -Body @{
            grant_type = "password"
            client_id  = $ClientId
            username   = $Username
            password   = $Password
        }
    $token = $tokenResp.access_token
    $pass++
    $results += [PSCustomObject]@{ Test="Get admin JWT"; Status="PASS"; Code=200 }
    Write-Host "  Token obtained (${($token.Length)} chars)" -ForegroundColor Green
} catch {
    $fail++
    $errMsg = $_.Exception.Message
    # Check for "Account is not fully set up" (MFA required action left behind)
    if ($errMsg -match "not fully set up") {
        $results += [PSCustomObject]@{ Test="Get admin JWT"; Status="FAIL"; Code="400 - Account has pending requiredActions (CONFIGURE_TOTP?). Clear via Keycloak Admin." }
    } else {
        $results += [PSCustomObject]@{ Test="Get admin JWT"; Status="FAIL"; Code=$errMsg.Substring(0, [Math]::Min(80, $errMsg.Length)) }
    }
}

if (-not $token) {
    Write-Host "`n[!] Cannot continue without JWT. Fix Keycloak login first." -ForegroundColor Red
    $results | Format-Table -AutoSize
    exit 1
}

$authHeaders = @{ Authorization = "Bearer $token" }

# ── 2. Auth router endpoints ──────────────────────────────────────────────────

Write-Host "[2] Testing auth router (/auth/...)..." -ForegroundColor Yellow

Test-Endpoint -Name "GET /auth/me" -Method GET `
    -Url "http://localhost:$BackendPort/auth/me" `
    -Headers $authHeaders

Test-Endpoint -Name "GET /auth/mfa-status" -Method GET `
    -Url "http://localhost:$BackendPort/auth/mfa-status" `
    -Headers $authHeaders

# ── 3. Admin router endpoints ─────────────────────────────────────────────────

Write-Host "[3] Testing admin router (/api/admin/...)..." -ForegroundColor Yellow

Test-Endpoint -Name "GET /api/admin/users" -Method GET `
    -Url "http://localhost:$BackendPort/api/admin/users" `
    -Headers $authHeaders

Test-Endpoint -Name "GET /api/admin/clients" -Method GET `
    -Url "http://localhost:$BackendPort/api/admin/clients" `
    -Headers $authHeaders

Test-Endpoint -Name "GET /api/admin/security/mfa" -Method GET `
    -Url "http://localhost:$BackendPort/api/admin/security/mfa" `
    -Headers $authHeaders

# ── 4. Vite proxy (if running on port 3000) ───────────────────────────────────

Write-Host "[4] Testing Vite proxy (localhost:3000)..." -ForegroundColor Yellow

$viteRunning = $false
try {
    $null = Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing -TimeoutSec 2
    $viteRunning = $true
} catch { }

if ($viteRunning) {
    Test-Endpoint -Name "Vite proxy /api/admin/users" -Method GET `
        -Url "http://localhost:3000/api/admin/users" `
        -Headers $authHeaders

    Test-Endpoint -Name "Vite proxy /auth/mfa-status" -Method GET `
        -Url "http://localhost:3000/auth/mfa-status" `
        -Headers $authHeaders
} else {
    $results += [PSCustomObject]@{ Test="Vite proxy"; Status="SKIP"; Code="Vite not running on :3000" }
    Write-Host "  Vite not running — skipping proxy tests" -ForegroundColor DarkYellow
}

# ── Report ─────────────────────────────────────────────────────────────────────

Write-Host "`n=== Results ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$total = $pass + $fail
Write-Host "Total: $total  Pass: $pass  Fail: $fail" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })

if ($fail -gt 0) {
    Write-Host "`n[!] SMOKE TEST FAILED — do NOT push until all endpoints pass." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n[OK] All smoke tests passed." -ForegroundColor Green
    exit 0
}
