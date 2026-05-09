# Tina-LogUtils.ps1
# PowerShell 日誌標準化工具
# 所有 Tina PS1 腳本都應使用此模組的 Write-Log 函數

$Global:TinaLogDir = "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs"
$Global:TinaLogSource = "PS"

function Initialize-LogDir {
    if (-not (Test-Path $Global:TinaLogDir)) {
        New-Item -ItemType Directory -Path $Global:TinaLogDir -Force | Out-Null
    }
}

function Write-Log {
    <#
    .SYNOPSIS
        統一日誌寫入函數
    .PARAMETER Level
        INFO | WARN | ERROR | DEBUG
    .PARAMETER Message
        日誌訊息
    .PARAMETER Source
        來源模組名稱（預設 PS）
    .PARAMETER LogFile
        指定日誌檔案（預設 tina_ps.log）
    #>
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("INFO", "WARN", "ERROR", "DEBUG")]
        [string]$Level,

        [Parameter(Mandatory=$true)]
        [string]$Message,

        [string]$Source = "PS",

        [string]$LogFile = "tina_ps.log"
    )

    Initialize-LogDir

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "$timestamp [$Level] [$Source] $Message"

    # 寫入檔案（UTF-8）
    $logPath = Join-Path $Global:TinaLogDir $LogFile
    try {
        Add-Content -Path $logPath -Value $logLine -Encoding UTF8
    } catch {
        # ignore write errors
    }

    # 主控台彩色輸出
    switch ($Level) {
        "INFO"  { Write-Host $logLine -ForegroundColor Cyan }
        "WARN"  { Write-Host $logLine -ForegroundColor Yellow }
        "ERROR" { Write-Host $logLine -ForegroundColor Red }
        "DEBUG" { Write-Host $logLine -ForegroundColor Gray }
    }
}

function Write-LogInfo {
    param([string]$Message, [string]$Source = "PS")
    Write-Log -Level INFO -Message $Message -Source $Source
}

function Write-LogWarn {
    param([string]$Message, [string]$Source = "PS")
    Write-Log -Level WARN -Message $Message -Source $Source
}

function Write-LogError {
    param([string]$Message, [string]$Source = "PS")
    Write-Log -Level ERROR -Message $Message -Source $Source
}

function Write-LogDebug {
    param([string]$Message, [string]$Source = "PS")
    Write-Log -Level DEBUG -Message $Message -Source $Source
}

# 匯出所有函數
Export-ModuleMember -Function Write-Log, Write-LogInfo, Write-LogWarn, Write-LogError, Write-LogDebug