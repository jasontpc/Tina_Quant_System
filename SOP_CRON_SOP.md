# Tina Cron Jobs — 標準作業程序（SOP）與自動排程
**版本：** v1.0
**建立日期：** 2026-05-09
**適用範圍：** 所有 Tina 系統的 Cron Jobs

---

## 0. 核心原則

1. **Delivery 優先** — 沒有 delivery 的 job = 無法通知 = 失效
2. **Timeout 寧可多** — Cold Start + 模型推理需要足夠時間
3. **Isolation 保護** — 主要系統用 isolated session
4. **標準化框架** — 所有腳本使用 `script_standards.py`

---

## 1. 腳本整合標準（Phase 2 以後）

### 1.1 新建腳本必須遵守

```python
from script_standards import ScriptStandard
std = ScriptStandard('job_name', 'TW')  # 或 'US'

# 主要邏輯

std.after_execute(success=True, signals=signals, metrics=metrics)
std.finalize()
```

### 1.2 現有腳本整合清單

| 腳本 | 狀態 | 優先順序 |
|:-----|:-----|:---------|
| us_ai_tech_daily.py | ✅ 已整合 | Phase 2 |
| us_margin_daily.py | 📋 待整合 | Phase 3 |
| leos_v65.py | 📋 待整合 | Phase 5 |
| tina_auto_learner.py | 📋 待整合 | Phase 4 |

---

## 2. Job 分類架構

### 2.1 L1 即時監控（每小時）

| Job | 功能 | Timeout |
|:----|:-----|:---------|
| Tina 風控檢查 | RSI / 持有天數 / 停損檢查 | 60s |

### 2.2 L2 日常分析（每日多次）

| Job | 功能 | Timeout |
|:----|:-----|:---------|
| Tina 自主決策五大層 | 完整市場分析 | 120s |
| US AI Tech 每日分析 | 美股 AI 科技掃描 | 120s |
| US Margin 每日分析 | 空頭/Margin 分析 | 120s |
| Leo v6.5 科技股波段 | 台股波段交易決策 | 600s |

### 2.3 L3 每週維護（每週）

| Job | 功能 | Timeout |
|:----|:-----|:---------|
| 台股 500 價值掃描（日）| 價值投資掃描 | 600s |
| 台股 500 成長掃描（日）| 成長股掃描 | 600s |
| S&P 500 價值掃描（週一）| 美股價值掃描 | 300s |
| 每週中度蒸餾 | Pattern 識別 | 180s |

### 2.4 L4 月度複雜（每月）

| Job | 功能 | Timeout |
|:----|:-----|:---------|
| 台股 500 完整回測（月）| 全面回測分析 | 600s |

---

## 3. 每日排程時間表

### 平日（週一至週五）

| 時間 | Job | 功能 |
|:-----|:----|:-----|
| 07:00 | Tina MEMORY 每日同步 | MEMORY.md 更新 |
| 07:30 | Tina 晨間宏觀快報 | Macro 整合 |
| 08:00 | Tina 日誌晨間檢討 | 錯誤掃描 |
| 08:30 | US AI Tech 每日分析 | 美股 AI 科技 |
| 08:45 | 每日開盤前策略報告 | 開盤策略 |
| 09:00 | Tina 大腦每日晨報 | 全市場統合 |
| 14:00 | Tina 盤後宏觀整合報告 | Macro 收盤 |
| 15:30 | US AI Tech 每日分析（第二波）| 美股掃描 |
| 16:00 | Tina 自主決策五大層 | 收盤分析 |
| 16:30 | Tina 日誌收盤檢討 | 日誌收盤 |
| 17:00 | Tina 自動學習擴充DB | 系統學習 |
| 18:00 | US Margin 每日分析 | 空頭分析 |
| 20:00 | 每日輕度蒸餾 | 記憶清理 |

### 週期性任務

| 時間 | Job | 功能 |
|:-----|:----|:-----|
| 每週一 08:00 | S&P 500 價值 + 生長掃描 | 美股一週開始 |
| 每週一 08:30 | US ETF 高股息掃描 | 美股 ETF |
| 每週三 08:00 | SOX 30 半導體掃描 | 半導體產業 |
| 每週五 08:00 | TW ETF 高股息掃描 | 台股 ETF |
| 每週五 14:00 | Tina 週Macro複審 | 每週 Macro |
| 每週日 10:00 | 台股 500 價值掃描 | 價值投資 |
| 每週日 10:00 | 台股 500 生長掃描 | 成長股 |
| 每週日 10:00 | Tina 日誌每週深度檢討 | 每週回顧 |

---

## 4. 資料流向架構

```
[Cron Job 觸發]
     ↓
[isolated session]
     ↓
┌─────────────────────────────────────┐
│  ScriptStandards (統一入口)           │
│  - before_execute() → 讀取脈絡        │
│  - 主要邏輯執行                       │
│  - after_execute() → 寫入記憶        │
│  - finalize() → 健康度追蹤           │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  輸出路由                           │
│  - short_term/working/*.json        │
│  - logs/job_run_log.json            │
│  - Telegram 摘要（如有 Bot Token）    │
└─────────────────────────────────────┘
```

---

## 5. 健康度追蹤系統

### 5.1 job_run_log.json 結構

```json
{
  "execution_id": "20260509_083000",
  "timestamp": "2026-05-09T08:30:00",
  "job_name": "us_ai_tech",
  "universe": "US",
  "duration_ms": 35678,
  "status": "ok",
  "errors": [],
  "warnings": [],
  "signal_count": 3,
  "metrics_summary": {
    "buy_count": 2,
    "watch_count": 1
  }
}
```

### 5.2 健康度閾值

| 狀態 | 條件 | 行動 |
|:-----|:-----|:-----|
| 🟢 OK | status=ok | 正常 |
| 🟡 WARNING | 有 warnings | 觀察 |
| 🔴 ERROR | status=error 或 errors 非空 | 立即檢查 |
| 🚨 CRITICAL | 連續 3 次 ERROR | 停用 job + 通知 |

### 5.3 自動健康度檢查（每 2 小時）

- 讀取 `logs/job_run_log.json`
- 識別最近 3 次執行有 ERROR 的 jobs
- 自動停用並發送 Telegram 警示

---

## 6. 快速命令參考

```bash
# 查看 Jobs 健康度
openclaw cron list --include-disabled

# 檢查 Error Jobs
openclaw cron list | findstr "error"

# 修復 Delivery
openclaw cron update <id> --delivery='{"mode":"announce","channel":"telegram","to":"1616824689"}'

# 緊急停用
openclaw cron disable <id>

# 緊急刪除
openclaw cron remove <id>
```

---

## 7. ScriptStandards 快速參考

```python
from script_standards import ScriptStandard

std = ScriptStandard('us_ai_tech', 'US')

# Step 1: 執行前
ctx = std.before_execute()
print(f"ID: {ctx['execution_id']}")

# Step 2: 執行主要邏輯（不改變）

# Step 3: 執行後
std.after_execute(
    success=True,
    signals=[{'symbol': 'NVDA', 'signal': 'BUY', 'rsi': 35}],
    metrics={'buy_count': 2, 'watch_count': 1}
)

# Step 4: 最終化
health = std.finalize()
print(f"Duration: {health['duration_ms']}ms")
```

---

## 8. 腳本整合檢查清單

每次新建腳本時：

- [ ] import `ScriptStandard`
- [ ] 建立 `std = ScriptStandard('job_name', 'TW')`
- [ ] 在主要邏輯後呼叫 `std.after_execute()`
- [ ] 在 `finally` 中呼叫 `std.finalize()`
- [ ] timeoutSeconds >= 120（複雜分析腳本）
- [ ] delivery.mode = "announce"
- [ ] delivery.to = "1616824689"
- [ ] sessionTarget = "isolated"

---

## 9. 維護日曆

| 日期 | 任務 |
|:-----|:-----|
| 每日 08:00 | 檢查 error jobs |
| 每日 22:00 | 健康度報告（Tina Cron Governor） |
| 每週日 10:00 | 蒸餾 + Pattern 識別 |
| 每月最後週日 | 深度蒸餾 + Framework 更新 |

---

_最後更新：2026-05-09 21:30 by Tina_