$RAY_DIR = "C:\Users\USER\.openclaw\agents\ray"
$LOG_DIR = "$RAY_DIR\logs"

if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

Write-Host "=== Ray Tina System Scheduler Setup ==="

$DailyAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ("-NoProfile -ExecutionPolicy Bypass -File " + $RAY_DIR + "\tina_ray_daily.ps1")
$WeeklyAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ("-NoProfile -ExecutionPolicy Bypass -File " + $RAY_DIR + "\tina_ray_weekly.ps1")

$TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoneBattery -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$TaskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$DailyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 08:30
Write-Host "[1/3] Creating Ray Tina Daily (Mon-Fri 08:30)..."
Unregister-ScheduledTask -TaskName "Ray Tina Daily" -Confirm:$false -EA SilentlyContinue
Register-ScheduledTask -TaskName "Ray Tina Daily" -Action $DailyAction -Trigger $DailyTrigger -Settings $TaskSettings -Principal $TaskPrincipal -Description "Ray Tina System 日間自動化" -Force | Out-Null
Write-Host "  [OK] Created"

$EveningTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 17:00
Write-Host "[2/3] Creating Ray Tina Evening (Mon-Fri 17:00)..."
Unregister-ScheduledTask -TaskName "Ray Tina Evening" -Confirm:$false -EA SilentlyContinue
Register-ScheduledTask -TaskName "Ray Tina Evening" -Action $DailyAction -Trigger $EveningTrigger -Settings $TaskSettings -Principal $TaskPrincipal -Description "Ray Tina System 傍晚自動化" -Force | Out-Null
Write-Host "  [OK] Created"

$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 22:00
Write-Host "[3/3] Creating Ray Tina Weekly (Fri 22:00)..."
Unregister-ScheduledTask -TaskName "Ray Tina Weekly" -Confirm:$false -EA SilentlyContinue
Register-ScheduledTask -TaskName "Ray Tina Weekly" -Action $WeeklyAction -Trigger $WeeklyTrigger -Settings $TaskSettings -Principal $TaskPrincipal -Description "Ray Tina 每週蒸餾" -Force | Out-Null
Write-Host "  [OK] Created"

Write-Host ""
Write-Host "=== Tasks Created ==="
Get-ScheduledTask | Where-Object { $_.TaskName -like "Ray Tina*" } | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -EA SilentlyContinue
    $nextRun = if ($info.NextRunTime) { $info.NextRunTime.ToString("MM/dd HH:mm") } else { "N/A" }
    Write-Host ("  " + $_.TaskName + " : Next=" + $nextRun + " | State=" + $_.State)
}
Write-Host ""
Write-Host "=== Setup Done ==="