# Registers (or updates) a daily Windows Task Scheduler job that refreshes the
# fantasy-football draft dataset by running pipeline/refresh.py.
#
# Runs as the CURRENT user with Interactive logon -> no elevation and no stored
# password required. A missed run (PC off/asleep at the scheduled time) fires as
# soon as the machine is available again.
#
#   Register:  powershell -ExecutionPolicy Bypass -File pipeline\register_refresh_task.ps1
#   Change time: pass -At (e.g. -At 5:30AM)
#   Remove:    Unregister-ScheduledTask -TaskName 'FF Data Refresh' -Confirm:$false
param(
  [string]$TaskName = 'FF Data Refresh',
  [datetime]$At = '6:00AM'
)
$ErrorActionPreference = 'Stop'

$proj    = Split-Path -Parent $PSScriptRoot          # pipeline\ -> project root
$refresh = Join-Path $PSScriptRoot 'refresh.py'
$py      = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not found on PATH - install Python or edit this script's `$py." }

$action    = New-ScheduledTaskAction -Execute $py -Argument "`"$refresh`"" -WorkingDirectory $proj
$trigger   = New-ScheduledTaskTrigger -Daily -At $At
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Principal $principal -Description 'Daily rebuild of the fantasy-football draft dataset (build_players.py + preview.py)' -Force | Out-Null

Write-Host "Registered '$TaskName' - runs daily at $($At.ToString('h:mm tt')) as $env:USERNAME."
Write-Host "Log: pipeline\logs\refresh.log"
Write-Host "Run now:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Remove:   Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
