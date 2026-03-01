# Test runner for common-auth backend SDK

param(
    [string]$Level = "unit",
    [switch]$Failed,
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$Quick
)

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Base command
$cmd = "python -m pytest"

# Determine test path
switch ($Level) {
    "unit" { $cmd += " tests/unit/" }
    "integration" { $cmd += " tests/integration/" }
    "e2e" { $cmd += " tests/e2e/" }
    "all" { $cmd += " tests/" }
    default { $cmd += " tests/unit/" }
}

# Add flags
if ($Failed) {
    $cmd += " --lf"
    Write-Host "Running previously failed tests only..." -ForegroundColor Yellow
}

if ($Quick) {
    $cmd += " -x"  # Stop on first failure
    Write-Host "Quick mode: Stopping on first failure" -ForegroundColor Yellow
}

if ($Verbose) {
    $cmd += " -vv --tb=long"
} else {
    $cmd += " -v --tb=short"
}

if ($Coverage) {
    $cmd += " --cov=src/common_auth --cov-report=html --cov-report=term-missing"
} else {
    $cmd += " --no-cov"
}

# Add color output
$cmd += " --color=yes"

# Execute
Write-Host "`n===========================================" -ForegroundColor Cyan
Write-Host " Common Auth Backend SDK - Test Runner" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Level: $Level" -ForegroundColor Green
Write-Host "Command: $cmd`n" -ForegroundColor Gray

$result = Invoke-Expression $cmd

# Display summary
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Some tests failed. Run with -Failed to retry failed tests only." -ForegroundColor Red
}

exit $LASTEXITCODE
