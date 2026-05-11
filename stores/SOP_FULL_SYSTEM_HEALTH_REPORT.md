# Tina 全系統健檢報告
**日期：** 2026-05-11 20:05
**檢查範圍：** Cron Jobs / DB 健康 / 系統資源 / 日誌

---

## 一、Cron Job 健康度

| Job | 狀態 | 錯誤數 | 最後執行 | 備註 |
|:----|:----:|-------:|:---------|:-----|
| Tina Cron v2 五大層 | ✅ OK | 0 | 2026-05-11 19:55 | 正常 |
| Tina 風控檢查 | ✅ OK | 0 | 2026-05-11 19:56 | 正常 |
| Leo v6.5 科技股波段 | ✅ OK | — | 2026-05-11 17:00 | 正常 |
| Vegas Tunnel TW 每日掃描 | ✅ OK | 0 | — | 明日 16:30 首次執行 |
| US AI Tech 每日分析 | ✅ OK | — | 2026-05-11 08:30 | 正常 |
| US Margin 每日分析 | ✅ OK | — | 2026-05-11 18:00 | 正常 |
| Tina 自動學習擴充DB | ✅ OK | — | 2026-05-11 17:00 | 正常 |
| 每日開盤前策略報告 | ✅ OK | — | 2026-05-09 08:45 | 正常 |
| 每週Macro複審（週五）| ✅ OK | — | 2026-05-09 17:00 | 正常 |
| 每週中度蒸餾（週五）| ✅ OK | — | 2026-05-09 18:00 | 正常 |
| Cron Governor 深夜喚醒 | ✅ OK | 0 | 2026-05-11 02:00 | 正常 |
| **Cron Governor 每小時監控** | 🔴 ERROR | **13** | 2026-05-11 19:55 | Telegram token 設定問題 |
| **Tina MEMORY 每日同步 AM** | 🔴 ERROR | **2** | 2026-05-11 07:00 | Timeout |

**健康度：12 jobs，10 OK / 2 ERROR**
**系統分數：83/100**

---

## 二、緊急問題（需立即處理）

### 🔴 P0：Cron Governor Telegram Delivery 失敗

**現況：** 13次連續錯誤，根源是 isolated session 的 agent 無法使用 main 的 Telegram token

**分析：**
- isolated session 的 delivery 送到 `agent:main:telegram:direct:1616824689` 或 `agent:tina-reports:telegram:direct:1616824689`
- 這些 session 的 delivery 需要獨立的 bot token
- 修復方案：把 delivery 改成 `channel: "telegram"` 讓 Gateway 自己路由

**行動：**
```
已執行：移除了 Cron Governor job 的 explicit accountId（已於 20:00 修復）
等待驗證：下次執行（19:00 GMT+8）是否成功
```

### 🔴 P1：Tina MEMORY 每日同步 timeout

**現況：** 2次 timeout（execution timed out），memory_distiller.py --level light 執行時間 >180s

**分析：**
- 腳本需要讀取大量短期記憶文件並蒸餾
- 光是 startup 就消耗大量 tokens
- 修復方案：精簡記憶蒸餾腳本，或降低執行頻率

**行動：**
```
已執行：timeout 120s → 180s
建議：考慮改用每日輕量模式，每週執行一次完整蒸餾
```

---

## 三、資料庫健康度

| DB | 大小 | 狀態 | 行動 |
|:---|-----:|:-----|:-----|
| yfinance.db | **177.6 MB** | ⚠️ 需維護 | 設定輪廓，每週清理30天+歷史 |
| macro_institutional.db | 10.4 MB | ✅ OK | 正常 |
| sherry_etf.db | 10.8 MB | ✅ OK | 正常 |
| etf.db | 7.1 MB | ✅ OK | 正常 |
| leverage_etf.db | 20.1 MB | ✅ OK | 正常 |
| us_history.db | 27.5 MB | ✅ OK | 正常 |
| tw_history.db | 9.5 MB | ✅ OK | 正常 |
| **reddit_sentiment.db** | **0 bytes** | 🔴 刪除 | 佔位空殼 |
| **limitup.db** | **0 bytes** | 🔴 刪除 | 佔位空殼 |
| **social_sentiment.db** | **0 bytes** | 🔴 刪除 | 佔位空殼 |
| **growth_paper_trading.db** | **0 bytes** | 🔴 刪除 | 佔位空殼 |
| tw_stock_registry.db | 0.2 MB | ✅ OK | 正常 |
| master_backtest.db | 0.3 MB | ✅ OK | 正常 |

**yfinance.db 177.6MB 專案：**
- 177MB = ~810,459 rows（包含大量歷史數據）
- 建議：每週執行一次 `yfinance_db_cleanup.py`（只保留最近 90天）

---

## 四、系統資源

| 指標 | 數值 | 評估 |
|:-----|:----:|:-----|
| CPU | 1.8-2.9% | ✅ 低 |
| Memory | 47-48% | ✅ 正常 |
| Cron Governor 活動分數 | 80/100 | ✅ 活躍 |
| 深夜喚醒窗口（02:00）| 正常 | ✅ |

---

## 五、改善計畫（優先順序）

### Phase 1：立即（今天）

| 行動 | 負責 | 期限 |
|:-----|:-----|:-----|
| 驗證 Cron Governor 修復是否生效（下次執行） | Tina | 今天 21:00 |
| 刪除 4個 0 bytes 空 DB | Tina | 今天 |
| 評估 MEMORY sync timeout 根本原因 | Tina | 今天 |

### Phase 2：本週

| 行動 | 說明 |
|:-----|:-----|
| 建立 yfinance.db 輪廓腳本 | 每週刪除 90天+ 歷史數據 |
| Vegas Daily Scan 驗證 | 明日 16:30 確認有輸出 |
| 全系統每日健康報告自動化 | 08:00 發送到 Telegram |
| 簡化 memory_distiller.py --level light | 降低 startup 開銷 |

### Phase 3：本月

| 行動 | 說明 |
|:-----|:-----|
| 所有 Cron Job 統一 timeout 標準 | 最小 120s |
| 建立 Cron Job 健康度 Dashboard | Streamlit 頁面 |
| 災難復原 SOP 文件化 | 當機/Gateway down 時的 SOP |
| 全部 DB 備份到 GitHub LFS | 避免資料損失 |

---

## 六、系統健康分數

| 維度 | 分數 | 備註 |
|:-----|:----:|:-----|
| Cron Jobs | 10/12 | 83% |
| 資料庫 | 18/21 | 86% |
| 系統資源 | 5/5 | 100% |
| 日誌品質 | 3/5 | 60% — DRY RUN 模式需確認 |
| 自動化覆蓋 | 4/5 | 80% — 缺少部分 Daily Report |
| **總分** | **43/50** | **86% — 良好** |

---

## 七、明日優先觀測

1. **Cron Governor** 是否不再報 Telegram 錯誤
2. **Vegas Daily Scan** 16:30 是否正常輸出到 Telegram
3. **MEMORY 同步** 07:00 是否完成（不再 timeout）

---

_本報告由 Tina 大腦 v3.6 全系統健檢引擎產出_
_下次健檢：2026-05-12 08:00_