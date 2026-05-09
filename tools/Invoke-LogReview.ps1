# Invoke-LogReview.ps1
# PowerShell 日誌檢討Wrapper
# 提供彩色輸出 + 記憶系統整合

param(
    [ValidateSet("morning", "evening", "full", "check-disk")]
    [string]$Mode = "morning",

    [int]$Days = 1,

    [switch]$DryRun
)

$logModule = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\tools\Tina-LogUtils.psm1"
$memModule = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\tools\Tina-MemoryUtils.psm1"
if (Test-Path $logModule) { Import-Module $logModule -Force }
if (Test-Path $memModule) { Import-Module $memModule -Force }

$ReviewScript = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\log_review.py"
$LogDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs"
$LogFile = "tina_ps.log"
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-ReviewLog {
    param([string]$Level, [string]$Message, [string]$Source = "LogReview")
    $line = "$ts [$Level] [$Source] $Message"
    $logPath = Join-Path $LogDir $LogFile
    try { Add-Content -Path $logPath -Value $line -Encoding UTF8 } catch {}
    switch ($Level) {
        "INFO"  { Write-Host $line -ForegroundColor Cyan }
        "WARN"  { Write-Host $line -ForegroundColor Yellow }
        "ERROR" { Write-Host $line -ForegroundColor Red }
        "SUMMARY" { Write-Host $line -ForegroundColor Green }
        default { Write-Host $line }
    }
}

Write-ReviewLog -Level INFO -Message "=== Tina Log Review Started | Mode: $Mode | Days: $Days ==="

# 執行 Python 檢討腳本
$args = "--mode $Mode"
if ($Days -gt 1) { $args += " --days $Days" }
if ($DryRun) { $args += " --dry-run" }

Write-ReviewLog -Level INFO -Message "Executing: python $ReviewScript $args"

try {
    $output = python $ReviewScript $args 2>&1
    $exitCode = $LASTEXITCODE

    # 彩色輸出報告
    $lines = $output -split "`n"
    foreach ($line in $lines) {
        if ($line -match "ERROR|Error|error") {
            Write-Host $line -ForegroundColor Red
        } elseif ($line -match "WARNING|Warn|⚠️") {
            Write-Host $line -ForegroundColor Yellow
        } elseif ($line -match "===|DONE|SUMMARY") {
            Write-Host $line -ForegroundColor Green
        } elseif ($line -match "INFO|Log Review") {
            Write-Host $line -ForegroundColor Cyan
        } else {
            Write-Host $line
        }
    }

    if ($exitCode -eq 0) {
        Write-ReviewLog -Level SUMMARY -Message "Log review completed successfully (exit 0)"
    } else {
        Write-ReviewLog -Level ERROR -Message "Log review exited with code: $exitCode"
    }

} catch {
    Write-ReviewLog -Level ERROR -Message "Exception during review: $_"
}

# 磁碟空間檢查（自動執行）
Write-ReviewLog -Level INFO -Message "Checking disk space..."
try {
    $diskOutput = python $ReviewScript --check-disk 2>&1
    if ($diskOutput -match "LOW DISK WARNING") {
        Write-ReviewLog -Level WARN -Message "LOW DISK detected!"
        Write-TinaMemory -Type "observation" -Summary "Low disk warning during log review" -Detail $diskOutput -Source "log_review" -Tags @("system", "disk", "alert") -Importance 9 -ExpiryDays 7
    }
} catch {}

# 寫入記憶（針對 evening/full）
if ($Mode -in ("evening", "full") -and -not $DryRun) {
    Write-ReviewLog -Level INFO -Message "Writing review to memory system..."
    $summary = "Log review $Mode: analyzed $(if($args -match '--days (\d+)'){$Matches[1]} else {'1'}) day(s)"
    Complete-TinaJob -JobName "log_review_$Mode" -Universe "MULTI" -Summary "Log review $Mode completed"
}

Write-ReviewLog -Level SUMMARY -Message "=== Tina Log Review Done ==="