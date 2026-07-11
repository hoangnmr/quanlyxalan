param(
    [string]$Time = "02:00"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Khong tim thay virtual environment: $python" }

$action = New-ScheduledTaskAction -Execute $python -Argument "scripts\backup_local.py --prune" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
Register-ScheduledTask -TaskName "KBCV-Daily-Backup" -Action $action -Trigger $trigger -Description "Khai-bao-Cang-vu daily SQLite backup" -Force
Write-Host "Da dang ky KBCV-Daily-Backup luc $Time."
