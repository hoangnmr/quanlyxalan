param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$server = Join-Path $projectRoot "backend\app.py"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 or newer is required."
}

Write-Host "Tan Thuan Port declaration app" -ForegroundColor Cyan
Write-Host "Open: http://$HostAddress`:$Port"
python $server --host $HostAddress --port $Port

