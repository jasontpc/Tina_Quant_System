# Tina Automation System - Cron Manager
param(
    [switch]$DryRun,
    [switch]$Remove
)

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
    Write-Host "Removing all Cron jobs..." -ForegroundColor Yellow
    $ids = Get-CurrentCronIds
    foreach ($id in $ids) {
        Write-Host "  Removing: $id" -ForegroundColor Gray
        openclaw cron rm $id 2>$null
    }
    Write-Host "Removed $($ids.Count) Cron jobs" -ForegroundColor Green
}

function Apply-CronTasks {
    if (-not (Test-Path $CronTasksFile)) {
        Write-Host "File not found: $CronTasksFile" -ForegroundColor Red
        return
    }

    Write-Host "Reading Cron tasks..." -ForegroundColor Cyan
    $lines = Get-Content $CronTasksFile -Encoding UTF8 | Where-Object { $_ -and -not $_.StartsWith("#") }
    
    $count = 0
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith("#")) { continue }
        
        $parts = $line -split '\|'
        if ($parts.Count -lt 3) { continue }
        
        $name = $parts[0].Trim()
        $schedule = $parts[1].Trim()
        $message = $parts[2].Trim()
        $target = if ($parts.Count -gt 3) { $parts[3].Trim() } else { "" }
        
        Write-Host ""
        Write-Host "Setting: $name" -ForegroundColor Yellow
        Write-Host "  Schedule: $schedule" -ForegroundColor Gray
        
        if ($DryRun) {
            Write-Host "  [DRY RUN] Not executed" -ForegroundColor Cyan
            continue
        }
        
        $cmd = "openclaw cron add --name `"$name`" --cron `"$schedule`" --message `"$message`""
        if ($target) {
            $cmd += " --to `"$target`""
        }
        
        Write-Host "  Executing..." -ForegroundColor Gray
        $result = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Success!" -ForegroundColor Green
            $count++
        } else {
            Write-Host "  Error: $result" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "Done! Applied $count Cron jobs" -ForegroundColor Green
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