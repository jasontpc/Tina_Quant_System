# Tina Automation System - Cron Manager
# 使用 Tina-LogUtils.psm1 + Tina-MemoryUtils.psm1

param(
    [switch]$DryRun,
    [switch]$Remove
)

# 匯入工具
$logModule = "$PSScriptRoot\Tina-LogUtils.psm1"
$memModule = "$PSScriptRoot\Tina-MemoryUtils.psm1"
if (Test-Path $logModule) { Import-Module $logModule -Force } else { Write-Host "[WARN] Tina-LogUtils.psm1 not found" -ForegroundColor Yellow }
if (Test-Path $memModule) { Import-Module $memModule -Force } else { Write-Host "[WARN] Tina-MemoryUtils.psm1 not found" -ForegroundColor Yellow }

$CronTasksFile = "$PSScriptRoot\..\cron_tasks.txt"

function Get-CurrentCronIds {
    $output = openclaw cron list 2>&1
    $ids = @()
    $lines = $output -split "`n"
    foreach ($line in $lines) {
        if ($line -match '^([a-f0-9-]+)\s') {
            $ids += $matches[1]
        }
    }
    return $ids
}

function Remove-AllCrons {
    Write-LogWarn "Removing all Cron jobs..."
    $ids = Get-CurrentCronIds
    $removed = 0
    foreach ($id in $ids) {
        Write-LogInfo "  Removing: $id"
        openclaw cron rm $id 2>$null
        $removed++
    }
    Write-LogInfo "Removed $removed Cron jobs"
    Write-TinaMemory -Type "decision" -Summary "Cleared all cron jobs: $removed jobs removed" -Detail "Manual cleanup via apply_cron.ps1 -Remove" -Source "cron_manager" -Tags @("cron", "cleanup") -Importance 7 -ExpiryDays 60
}

function Apply-CronTasks {
    if (-not (Test-Path $CronTasksFile)) {
        Write-LogError "File not found: $CronTasksFile"
        return
    }

    Write-LogInfo "Reading Cron tasks from: $CronTasksFile"
    $lines = Get-Content $CronTasksFile -Encoding UTF8 | Where-Object { $_ -and -not $_.StartsWith("#") }

    $count = 0
    $errors = 0
    $skipped = 0

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith("#")) { continue }

        $parts = $line -split '\|'
        if ($parts.Count -lt 3) { continue }

        $name = $parts[0].Trim()
        $schedule = $parts[1].Trim()
        $message = $parts[2].Trim()
        $target = if ($parts.Count -gt 3) { $parts[3].Trim() } else { "" }

        Write-LogInfo "Setting: $name | Schedule: $schedule"

        if ($DryRun) {
            Write-LogInfo "  [DRY RUN] Not executed"
            $skipped++
            continue
        }

        $cmd = "openclaw cron add --name `"$name`" --cron `"$schedule`" --message `"$message`""
        if ($target) {
            $cmd += " --to `"$target`""
        }

        $result = Invoke-Expression $cmd 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-LogInfo "  Success!"
            $count++

            # 寫入成功記憶
            Write-TinaMemory -Type "decision" -Summary "Cron added: $name" -Detail "schedule=$schedule" -Source "cron_manager" -Tags @("cron", "added") -Importance 5 -ExpiryDays 30
        } else {
            Write-LogError "  Error: $result"
            $errors++
            Write-TinaMemory -Type "lesson" -Summary "Cron add failed: $name" -Detail "Error: $result | schedule: $schedule" -Source "cron_manager" -Tags @("cron", "error") -Importance 7 -ExpiryDays 90
        }
    }

    Write-LogInfo "Done! Applied $count Cron jobs | Errors: $errors | Skipped: $skipped"

    # 寫入彙總記憶
    $metrics = @{
        "applied" = $count
        "errors" = $errors
        "skipped" = $skipped
        "timestamp" = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    } | ConvertTo-Json -Compress
    Complete-TinaJob -JobName "cron_manager" -Universe "MULTI" -Metrics $metrics -Summary "Cron apply: $count applied, $errors errors"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tina Automation System - Cron Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($Remove) {
    Remove-AllCrons
} else {
    Apply-CronTasks
}