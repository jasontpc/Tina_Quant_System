# Invoke-Wisdom.ps1
# PowerShell 累計智慧界面
# 讓 PowerShell 腳本能直接存取/寫入智慧庫

param(
    [ValidateSet("aggregate", "check", "promote", "patterns", "lessons")]
    [string]$Action = "check",

    [int]$Days = 14,

    [string]$MemoryId = ""
)

$logModule = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\tools\Tina-LogUtils.psm1"
$memModule = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\tools\Tina-MemoryUtils.psm1"
if (Test-Path $logModule) { Import-Module $logModule -Force }
if (Test-Path $memModule) { Import-Module $memModule -Force }

$WisdomScript = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\accumulated_wisdom.py"
$StoresDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores"

Write-LogInfo "Wisdom action: $Action (days=$Days)" -Source "Wisdom"

switch ($Action) {
    "aggregate" {
        Write-LogInfo "Aggregating last $Days days of memories..." -Source "Wisdom"
        python $WisdomScript aggregate --days $Days
        Write-LogInfo "Aggregation complete" -Source "Wisdom"
    }
    "check" {
        Write-LogInfo "Checking wisdom store status..." -Source "Wisdom"
        python $WisdomScript check

        # 也印出 PowerShell 端寫入的記憶統計
        $stDir = Join-Path $StoresDir "short_term"
        if (Test-Path $stDir) {
            $psFiles = Get-ChildItem $stDir -Filter "*_*.json" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) }
            $psCount = ($psFiles | Where-Object { $_.Name -match "^20\d{6}_" }).Count
            Write-LogInfo "PS-written memories (7d): $psCount files" -Source "Wisdom"
        }
    }
    "promote" {
        if (-not $MemoryId) {
            Write-LogError "Missing --MemoryId" -Source "Wisdom"
            exit 1
        }
        Write-LogInfo "Promoting memory: $MemoryId" -Source "Wisdom"
        python $WisdomScript promote --id $MemoryId
    }
    "patterns" {
        Write-LogInfo "Reading patterns from wisdom store..." -Source "Wisdom"
        $patterns = Get-Content (Join-Path $StoresDir "long_term\patterns.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $patterns.PSObject.Properties | Where-Object { $_.Name -eq "patterns" } | ForEach-Object {
            $_.Value | ForEach-Object {
                $p = $_
                Write-Host "  [$($p.status)] $($p.name.Substring(0, [Math]::Min(50, $p.name.Length))) | hit=$($p.hit_rate.ToString('P0')) occ=$($p.occurrences)"
            }
        }
    }
    "lessons" {
        Write-LogInfo "Reading lessons from wisdom store..." -Source "Wisdom"
        $lessons = Get-Content (Join-Path $StoresDir "long_term\lessons.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $lessons.PSObject.Properties | Where-Object { $_.Name -eq "lessons" } | ForEach-Object {
            $_.Value | ForEach-Object {
                $l = $_
                Write-Host "  [$($l.date)] $($l.summary.Substring(0, [Math]::Min(60, $l.summary.Length)))"
            }
        }
    }
}

Write-LogInfo "Wisdom action '$Action' done" -Source "Wisdom"