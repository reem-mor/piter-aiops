# Start PITER AiOps locally on http://127.0.0.1:8080 (Windows)
param(
    [string]$Profile = "reemmor",
    [switch]$Gunicorn
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Missing venv at $Python. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt"
}

$env:AWS_PROFILE = $Profile
$env:AWS_DEFAULT_REGION = "us-east-1"
Set-Location $Root

# Free port 8080 if something stale is listening
$conn = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    $pid8080 = $conn.OwningProcess
    Write-Host "Stopping process on :8080 (PID $pid8080)..." -ForegroundColor Yellow
    Stop-Process -Id $pid8080 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "Starting PITER on http://127.0.0.1:8080 (profile=$Profile)..." -ForegroundColor Cyan
if ($Gunicorn) {
    Write-Error "gunicorn does not run on Windows (needs Linux). Use run-local.ps1 or: docker compose up --build"
}
& $Python app.py
