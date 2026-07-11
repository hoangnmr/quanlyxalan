param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.13 or newer is required."
}

Set-Location $projectRoot

python -m alembic upgrade head

Write-Host "Tan Thuan Port declaration app (FastAPI)" -ForegroundColor Cyan
Write-Host "Open: http://$HostAddress`:$Port"
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

python -m uvicorn backend.app:app --host $HostAddress --port $Port --reload
