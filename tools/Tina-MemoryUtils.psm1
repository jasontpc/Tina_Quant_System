# Tina-MemoryUtils.psm1
# PowerShell 記憶系統整合工具
# 與 Python brain_memory_cli.py 無縫整合，累積智慧

$Global:TinaStoresDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores"
$Global:TinaScriptsDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts"
$Global:TinaLogDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs"
$Global:TinaBaseDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

# ===== 日誌 =====

function Write-TinaLog {
    param([string]$Level, [string]$Message, [string]$Source = "Memory")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts [$Level] [$Source] $Message"
    $logPath = Join-Path $Global:TinaLogDir "tina_ps.log"
    try { Add-Content -Path $logPath -Value $line -Encoding UTF8 } catch {}
    switch ($Level) {
        "INFO"  { Write-Host $line -ForegroundColor Cyan }
        "WARN"  { Write-Host $line -ForegroundColor Yellow }
        "ERROR" { Write-Host $line -ForegroundColor Red }
        default { Write-Host $line }
    }
}

# ===== 記憶讀寫 =====

function Read-TinaShortTerm {
    <#
    .SYNOPSIS
        讀取最近N天的短期記憶
    .PARAMETER Days
        天數（預設 7）
    .PARAMETER Type
        記憶類型：observation, decision, lesson, pattern, metric
    #>
    param(
        [int]$Days = 7,
        [string]$Type = $null
    )

    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" read --type memories --days $Days"
    if ($Type) {
        $cmd += " --type $Type"
    }

    Write-TinaLog -Level INFO -Message "Reading short-term memories (days=$Days, type=$Type)" -Source "Memory"

    try {
        $output = Invoke-Expression $cmd 2>&1
        return $output
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to read short-term: $_" -Source "Memory"
        return $null
    }
}

function Write-TinaMemory {
    <#
    .SYNOPSIS
        寫入短期記憶（透過 brain_memory_cli.py）
    .PARAMETER Type
        記憶類型：observation, decision, lesson, pattern, metric
    .PARAMETER Summary
        摘要（必填）
    .PARAMETER Detail
        詳細內容
    .PARAMETER Source
        來源（預設 PS）
    .PARAMETER Tags
        標籤（陣列）
    .PARAMETER Importance
        重要性 1-10（預設 5）
    .PARAMETER ExpiryDays
        過期天數（預設 30）
    #>
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("observation", "decision", "lesson", "pattern", "metric", "news", "framework_change")]
        [string]$Type,

        [Parameter(Mandatory=$true)]
        [string]$Summary,

        [string]$Detail = "",

        [string]$Source = "PS",

        [string[]]$Tags = @(),

        [int]$Importance = 5,

        [int]$ExpiryDays = 30
    )

    $tagsStr = ($Tags -join ",")
    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" write --type $Type --summary `"$Summary`" --detail `"$Detail`" --source $Source --tags `"$tagsStr`" --importance $Importance --expiry $ExpiryDays"

    Write-TinaLog -Level INFO -Message "Write memory: [$Type] $Summary" -Source "Memory"

    try {
        $output = Invoke-Expression $cmd 2>&1
        Write-TinaLog -Level INFO -Message "Result: $output" -Source "Memory"
        return $output
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to write memory: $_" -Source "Memory"
        return $null
    }
}

function Write-TinaObservation {
    <#
    .SYNOPSIS
        快速寫入觀測記憶（觀察到某個市場現象）
    #>
    param(
        [string]$Summary,
        [string]$Detail = "",
        [string[]]$Tags = @(),
        [int]$Importance = 5
    )
    Write-TinaMemory -Type "observation" -Summary $Summary -Detail $Detail -Source "PS" -Tags $Tags -Importance $Importance -ExpiryDays 30
}

function Write-TinaDecision {
    <#
    .SYNOPSIS
        快速寫入決策記憶（為什麼做某個決定）
    #>
    param(
        [string]$Summary,
        [string]$Detail = "",
        [string[]]$Tags = @(),
        [int]$Importance = 7
    )
    Write-TinaMemory -Type "decision" -Summary $Summary -Detail $Detail -Source "PS" -Tags $Tags -Importance $Importance -ExpiryDays 60
}

function Write-TinaLesson {
    <#
    .SYNOPSIS
        快速寫入Lesson（失敗/成功教訓）
    #>
    param(
        [string]$Summary,
        [string]$Detail = "",
        [string[]]$Tags = @(),
        [int]$Importance = 8
    )
    Write-TinaMemory -Type "lesson" -Summary $Summary -Detail $Detail -Source "PS" -Tags $Tags -Importance $Importance -ExpiryDays 90
}

# ===== 長期記憶讀取 =====

function Get-TinaPatterns {
    <#
    .SYNOPSIS
        讀取長期累積的市場 Pattern
    .PARAMETER Universe
        TW / US / SOX / MULTI
    #>
    param([string]$Universe = "")

    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" read --type patterns"
    if ($Universe) {
        $cmd += " --universe $Universe"
    }

    Write-TinaLog -Level INFO -Message "Reading patterns (universe=$Universe)" -Source "Memory"

    try {
        $output = Invoke-Expression $cmd 2>&1
        return $output
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to read patterns: $_" -Source "Memory"
        return $null
    }
}

function Get-TinaLessons {
    <#
    .SYNOPSIS
        讀取長期累積的 Lessons
    #>
    Write-TinaLog -Level INFO -Message "Reading lessons" -Source "Memory"
    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" read --type lessons"
    try {
        return Invoke-Expression $cmd 2>&1
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to read lessons: $_" -Source "Memory"
        return $null
    }
}

# ===== 智慧累積 =====

function Add-TinaWisdom {
    <#
    .SYNOPSIS
        將 PowerShell 腳本結果轉化為智慧寫入記憶系統
    .PARAMETER EventType
        scan / check / monitor / decision
    .PARAMETER EventData
        事件資料（Hashtable）
    .PARAMETER Tags
        標籤
    #>
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("scan", "check", "monitor", "decision", "trade", "alert")]
        [string]$EventType,

        [Parameter(Mandatory=$true)]
        [hashtable]$EventData,

        [string[]]$Tags = @()
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    switch ($EventType) {
        "scan" {
            $summary = "$($EventData.symbol): $($EventData.action) @ $($EventData.price)"
            $detail = "RSI=$($EventData.rsi), 持有=$($EventData.days)天, 報酬=$($EventData.gain)%"
            $importance = 6
            $tags = @($EventData.universe) + $Tags
            Write-TinaObservation -Summary $summary -Detail $detail -Tags $tags -Importance $importance
        }
        "check" {
            $summary = "系統檢查: $($EventData.status)"
            $detail = "項目=$($EventData.items), 結果=$($EventData.result)"
            $tags = @("system_check") + $Tags
            Write-TinaObservation -Summary $summary -Detail $detail -Tags $tags -Importance 4
        }
        "monitor" {
            $summary = "監控: $($EventData.metric) = $($EventData.value)"
            $detail = "閾值=$($EventData.threshold), 狀態=$($EventData.status)"
            $tags = @("monitor") + $Tags
            Write-TinaObservation -Summary $summary -Detail $detail -Tags $tags -Importance 5
        }
        "decision" {
            $summary = "決策: $($EventData.action) $($EventData.target)"
            $detail = "原因=$($EventData.reason), 風險=$($EventData.risk)"
            $tags = @("decision") + $Tags
            Write-TinaDecision -Summary $summary -Detail $detail -Tags $tags -Importance 8
        }
        "trade" {
            $summary = "交易: $($EventData.type) $($EventData.symbol) @ $($EventData.price)"
            $detail = "數量=$($EventData.qty), 原因=$($EventData.reason), P/L=$($EventData.pnl)"
            $tags = @("trade", $EventData.symbol) + $Tags
            Write-TinaDecision -Summary $summary -Detail $detail -Tags $tags -Importance 9
        }
        "alert" {
            $summary = "警報: $($EventData.message)"
            $detail = "level=$($EventData.level), 標的=$($EventData.target)"
            $tags = @("alert", "system") + $Tags
            Write-TinaMemory -Type "observation" -Summary $summary -Detail $detail -Tags $tags -Importance 9 -ExpiryDays 7
        }
    }
}

# ===== Job 完成寫入 =====

function Complete-TinaJob {
    <#
    .SYNOPSIS
        Job 執行完畢後寫入記憶（封裝 brain_memory_cli.py complete）
    .PARAMETER JobName
        Job 名稱
    .PARAMETER Universe
        TW / US / MULTI
    .PARAMETER Signals
        信號（JSON 字串）
    .PARAMETER Metrics
        指標（JSON 字串）
    .PARAMETER Summary
        摘要描述
    #>
    param(
        [string]$JobName,
        [string]$Universe = "MULTI",
        [string]$Signals = "",
        [string]$Metrics = "",
        [string]$Summary = ""
    )

    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" complete --job $JobName --universe $Universe"
    if ($Signals) { $cmd += " --signals `"$Signals`"" }
    if ($Metrics) { $cmd += " --metrics `"$Metrics`"" }
    if ($Summary) { $cmd += " --summary `"$Summary`"" }

    Write-TinaLog -Level INFO -Message "Completing job: $JobName" -Source "Memory"

    try {
        $output = Invoke-Expression $cmd 2>&1
        Write-TinaLog -Level INFO -Message "Job memory written: $output" -Source "Memory"
        return $output
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to complete job: $_" -Source "Memory"
        return $null
    }
}

# ===== Dashboard =====

function Show-TinaBrainDashboard {
    <#
    .SYNOPSIS
        顯示大腦記憶 Dashboard
    #>
    Write-TinaLog -Level INFO -Message "Building brain dashboard..." -Source "Memory"
    $cmd = "python `"$Global:TinaStoresDir\..\scripts\brain_memory_cli.py`" dashboard"
    try {
        $output = Invoke-Expression $cmd 2>&1
        Write-Host $output
        return $output
    } catch {
        Write-TinaLog -Level ERROR -Message "Failed to build dashboard: $_" -Source "Memory"
        return $null
    }
}

# 匯出所有函數
Export-ModuleMember -Function Write-TinaLog, Read-TinaShortTerm, Write-TinaMemory, `
    Write-TinaObservation, Write-TinaDecision, Write-TinaLesson, `
    Get-TinaPatterns, Get-TinaLessons, `
    Add-TinaWisdom, Complete-TinaJob, Show-TinaBrainDashboard