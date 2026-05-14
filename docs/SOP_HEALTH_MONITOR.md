# Tina Cron Job 健康度自動監控排程
**版本：** v1.0
**建立日期：** 2026-05-09

---

## 概述

本排程用於自動化 Tina Cron Job 健康度監控，確保所有 Jobs 正常運行。

### 監控頻率

| Job | 頻率 | 功能 | Timeout |
|:----|:-----|:-----|:---------|
| Cron Job 健康度自動監控 | 每 2 小時 | 檢查 job_run_log.json + 識別問題 Jobs | 60s |

---

## 自動化流程

```
[每 2 小時]
     ↓
┌─────────────────────────────────────┐
│  cron_health_monitor.py              │
│  - 讀取 job_run_log.json             │
│  - 分析每個 job 的健康度              │
│  - 識別 ERROR / WARNING jobs         │
│  - 寫入 health_reports/              │
│  - 發送 Telegram（如果有问题）         │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  判定邏輯                           │
│  - 連續 3 次 ERROR → CRITICAL       │
│  - 1 次 ERROR → ERROR               │
│  - 連續 3 次 WARNING → WARNING       │
│  - 全OK → HEALTHY                   │
└─────────────────────────────────────┘
```

---

## 健康度報告位置

- 即時報告：`stores/health_reports/latest.json`
- 每日報告：`stores/health_reports/health_report_YYYYMMDD.json`

---

## 判斷標準

| 狀態 | 條件 | 建議動作 |
|:-----|:-----|:---------|
| 🚨 CRITICAL | 連續 3 次 ERROR | 立即停用 job + 通知 Jo |
| ❌ ERROR | 1 次 ERROR | 檢查錯誤日誌 |
| ⚠️ WARNING | 連續 3 次 WARNING | 觀察中 |
| ✅ HEALTHY | 全部 OK | 正常運行 |
| ❓ UNKNOWN | 無執行記錄 | 檢查是否正常排程 |

---

_建立：2026-05-09 by Tina_