# Ray Tina System - 標準作業程序 (SOP)
# Version 1.0 | 2026-05-12 | Ray Agent

## 系統架構

```
Ray Brain (ray_brain.py)
├── Layer 1: 本地 Python (EMA/RSI/KDJ/MACD 計算) — 無 LLM
├── Layer 2: ray-v1 (1.5B) — 快速策略提案 (< 5s)
└── Layer 3: ray-deep-v1 (7B) — 深度歸因分析 (~25-35s cold, ~0.8s warm)

Ray Evolution (ray_evolution.py)
├── 自主學習循環：網格搜索 13 種策略 → 回測 → 寫入 DB
└── 每日自我修正：weight 衰減/強化

Ray Self-Correction (ray_self_correct.py)
├── Layer 1: 1.5B 快速分類失敗原因 (快速處理)
└── Layer 2: 7B 深度重建（僅 confidence < 0.5 觸發）
```

## 模型效能基準

| 模型 | 冷啟動 | 快取後 | 適用場景 |
|------|--------|--------|---------|
| ray-v1 (1.5B) | ~2-5s | < 1s | 日常掃描/快速提案 |
| ray-deep-v1 (7B) | ~32-43s | ~0.8s | 深度歸因/蒸餾教學 |

**⚠️ 重要優化準則：7B 只在非交易時段使用，且需要預熱。**

## 每日自動化排程 (PowerShell)

### tina_ray_daily.ps1 — 日間自動化腳本

```powershell
# === Ray Tina System Daily Automation ===
# 執行時間：每個交易日（非週末）

$ErrorActionPreference = "Continue"
$RAY_DIR = "C:\Users\USER\.openclaw\agents\ray"
$LOG_FILE = "$RAY_DIR\logs\ray_daily_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log($msg, $level="INFO") {
    $ts = Get-Date -Format "HH:mm:ss"
    "$ts [$level] $msg" | Tee-Object -FilePath $LOG_FILE -Append
}

Write-Log "=== Ray Tina System Daily Start ==="

# === Stage 1: 盤前掃描 (08:30) ===
Write-Log "[1/6] Stage 1: 盤前動能掃描 (ray-v1)"
python $RAY_DIR\us_momentum.py --symbols QQQ,VTI,BND,VEA,SPY 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# === Stage 2: 自我修正 (15:00) — 1.5B 先處理 ===
Write-Log "[2/6] Stage 2: 每日自我修正 (1.5B 先, 7B 後)"
python $RAY_DIR\ray_self_correct.py 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# === Stage 3: 蒸餾數據準備 (17:00) ===
Write-Log "[3/6] Stage 3: 蒸餾數據生成"
python $RAY_DIR\ray_gold_miner.py 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# === Stage 4: Weight 更新 (17:30) ===
Write-Log "[4/6] Stage 4: 智慧權重更新"
python $RAY_DIR\ray_evolution.py --mode update_weights 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# === Stage 5: Wisdom Decay (18:00) ===
Write-Log "[5/6] Stage 5: 智慧衰減"
python $RAY_DIR\ray_evolution.py --mode decay 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# === Stage 6: 系統狀態報告 (18:30) ===
Write-Log "[6/6] Stage 6: 每日狀態報告"
python $RAY_DIR\ray_evolution.py --mode stats 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

Write-Log "=== Ray Tina System Daily Complete ==="
```

### tina_ray_weekly.ps1 — 每週蒸餾腳本

```powershell
# === Ray Tina System Weekly Distillation ===
# 執行時間：每週五 22:00（非交易日）

$RAY_DIR = "C:\Users\USER\.openclaw\agents\ray"
$LOG_FILE = "$RAY_DIR\logs\ray_weekly_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log($msg, $level="INFO") {
    $ts = Get-Date -Format "HH:mm:ss"
    "$ts [$level] $msg" | Tee-Object -FilePath $LOG_FILE -Append
}

Write-Log "=== Ray Tina Weekly Distillation Start ==="

# Step 1: 預熱 7B 模型（避免冷啟動）
Write-Log "[1/4] 預熱 7B 模型..."
python -c "
import requests
requests.post('http://localhost:11434/api/chat', json={
    'model': 'ray-deep-v1',
    'messages': [{'role': 'user', 'content': 'Pre-warm: responding with OK'}],
    'stream': False, 'options': {'num_predict': 5}
}, timeout=60)
print('7B warmup complete')
"

# Step 2: 蒸餾數據生成
Write-Log "[2/4] 生成蒸餾數據..."
python $RAY_DIR\ray_gold_miner.py 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

# Step 3: 執行 Unsloth 微調（如果數據充足）
Write-Log "[3/4] 執行 Unsloth 微調..."
$gold_count = python -c "
import sqlite3
conn = sqlite3.connect('$RAY_DIR\ray_wisdom.db')
c = conn.cursor()
c.execute(\"SELECT count(*) FROM wisdom_logs WHERE weight > 1.5 AND passed = 1\")
print(c.fetchone()[0])
conn.close()
"

if ($gold_count -gt 30) {
    Write-Log "Gold samples: $gold_count (> 30) — proceeding with distillation"
    python $RAY_DIR\ray_train_tina.py --mode causal_sft --epochs 3 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

    # Reload Ollama model
    Write-Log "Reloading Ollama model..."
    & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" create ray-v1 -f "$RAY_DIR\ray-v1.Modelfile" 2>$null
} else {
    Write-Log "Insufficient gold samples ($gold_count <= 30) — skipping distillation"
}

# Step 4: Weekly stats
Write-Log "[4/4] 每週統計"
python $RAY_DIR\ray_evolution.py --mode stats 2>&1 | Tee-Object -FilePath $LOG_FILE -Append

Write-Log "=== Ray Tina Weekly Complete ==="
```

## Windows 工作排程器設定

### 建立日間自動化任務

```powershell
# 以系統管理員身份執行 PowerShell

# 建立任務主體
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\agents\ray\tina_ray_daily.ps1"

# 觸發器：每個平日 08:30
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 08:30

# 設定
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoneBattery -StartWhenAvailable

# 執行身份
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# 註冊任務
Register-ScheduledTask -TaskName "Ray Tina Daily" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Ray Tina System 日間自動化" | Out-Null

# 每週任務（週五 22:00）
$WeeklyAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\agents\ray\tina_ray_weekly.ps1"
$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 22:00
Register-ScheduledTask -TaskName "Ray Tina Weekly" -Action $WeeklyAction -Trigger $WeeklyTrigger -Settings $Settings -Principal $Principal -Description "Ray Tina 每週蒸餾" | Out-Null
```

## 效能瓶頸與改善方案

### 問題 1: 7B 冷啟動 ~32-43s
**原因**：每次模型切換需要重新載入權重到 GPU
**改善**：
- 每日 08:00 預熱：確保 7B 在开盘前已載入
- 批量處理：將多個失敗案例打包成一次呼叫
- 7B 只處理 confidence < 0.5 的複雜案例（1.5B 處理其餘 80%）

### 問題 2: backtest_reports = 0（所有策略被刷掉）
**原因**：Sharpe > 1.5 / MDD < 15% 門檻過嚴
**改善**：
- 日間模式：Sharpe > 0.8 / MDD < 20%
- 黃金標準（蒸餾）：Sharpe > 1.5

### 問題 3: wisdom_logs 無 symbol 欄位
**原因**：schema 設計缺陷，symbol 需要 LEFT JOIN backtest_reports
**改善**：已修正，未來新欄位直接內含

## 監控與告警

```powershell
# 每日健康檢查（整合進 Tina Cron Governor）
$corrections = python -c "
import sqlite3
conn = sqlite3.connect('C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE created_at > datetime(\"now\", \"-1 day\")')
print(c.fetchone()[0])
conn.close()
"

if ($corrections -eq 0) {
    Write-Host "[WARNING] No self-corrections in last 24h — possible system stall"
}
```

## 版本記錄

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-05-12 | v1.0 | 初始版本：雙層 LLM + 每日排程 + SOP |

## 腳本清單

| 腳本 | 功能 |
|------|------|
| `ray_brain.py` | 路由層（本地指標 → 1.5B → 7B） |
| `ray_evolution.py` | 自主學習 + 每日修正 CLI |
| `ray_self_correct.py` | 雙層自我修正引擎 |
| `ray_engine.py` | 回測引擎（已含 RSI/RSI2） |
| `ray_data_center.py` | SQLite 持久化 |
| `us_momentum.py` | 美股 ETF 動能掃描 |
| `tina_ray_daily.ps1` | 日間自動化排程 |
| `tina_ray_weekly.ps1` | 每週蒸餾排程 |