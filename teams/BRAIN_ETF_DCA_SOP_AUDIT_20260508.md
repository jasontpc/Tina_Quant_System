# Tina 大腦 — ETF DCA 結構與 SOP 審查報告
**日期：** 2026-05-08 01:00
**主題：** 月度 ETF DCA 結構、標準作業程序、提出改善措施

---

## 📊 現況：兩套 DCA 系統並存

| 團隊 | 職責 | 覆蓋範圍 | 問題 |
|:----:|:-----|:---------|:-----|
| **Ray** | TW ETF DCA | 0050/00646/00878/00919（台股4檔）| ⚠️ 只看台股，無美股 |
| **Sherry** | US ETF DCA | SPY/QQQ/VEA/VWO/VIG/SCHD/VYM/BND（過廣）| ⚠️ 清單與 Jo 需求脫節 |
| **兩者分工** | ❌ 未明確定義 | ⚠️ 重疊 + 空白 |

**Jo 指定的 DCA 組合（由誰管？）**

| 倉位 | 比例 | 目前負責 | 狀態 |
|:-----|:----:|:---------|:-----|
| VOO | 70% | ❌ 無人 | 缺口 |
| QQQ | 30% | ❌ 無人 | 缺口 |
| VTI | 可選 | ❌ 無人 | 缺口 |
| SCHD | 衛星 | ❌ 無人（Sherry 有但未聚焦）|

---

## 🔍 Ray DCA 分析（完整）

### 正式腳本
| 腳本 | 功能 | Cron |
|:-----|:-----|:-----|
| `dca_market_brief.py` | 每日市場分析（4檔台股）| 平日 16:10 ✅ |
| `dca_backtest.py` | DCA 回測 | 非 cron |
| `ray_dca_portfolio.py` | 組合建議 | 非 cron |
| `ray_alert_agent.py` | 警報 | 非 cron |

### 現有流程（dca_market_brief.py）

```
每日 16:10 → 抓 TWII RSI → 對 4 檔 ETF 計算：
  - MA60 position（偏離度）
  - RSI（14日）
  - 60日高點位置（position）
  → 輸出 action：
    TWII pos > 20 or RSI > 75 → HOLD x0
    TWII pos > 10 or RSI > 65 → HOLD x0.5
    position < -15 → BUY x1.5
    position < -5 → BUY x1
    else → DCA x1
```

### 缺失

| # | 問題 | 嚴重性 |
|:-:|:-----|:-------:|
| 1 | **沒有 VOO / QQQ**（Jo 的核心倉位）| 🔴 高 |
| 2 | **沒有月度報告**（只有每日摘要）| 🟡 中 |
| 3 | **沒有每月執行提醒**（Jo 何時 DCA？）| 🟡 中 |
| 4 | **沒有歷史累計成本追蹤**（DCA 多久了？均價？）| 🟡 中 |
| 5 | **沒有與 Jo 實際帳戶同步**（誰管實際買入？）| 🔴 高 |

---

## 🔍 Sherry DCA 分析（完整）

### 正式腳本
| 腳本 | 功能 | Cron |
|:-----|:-----|:-----|
| `scripts/sherry_daily_check.py` | 每日 ETF 健康檢查 | 08:00 ✅ |
| `scripts/sherry_autonomous.py` | ETF 自主學習/建庫 | 非 cron |
| `scripts/sherry_screener.py` | ETF 篩選 | 非 cron |

### Watchlist（16檔過廣）
```
XLV/VHT/GLD/TLT/LQD/AGG/BND/HYG/SPY/QQQ/VEA/VWO/VIG/SCHD/VYM/XLK/XLF/XLE/XLRE/EEM/USO
```

### 問題

| # | 問題 | 嚴重性 |
|:-:|:-----|:-------:|
| 1 | **清單沒有 VOO**（Jo 的核心）| 🔴 高 |
| 2 | **16檔太寬，無聚焦** | 🟡 中 |
| 3 | **與 Ray 分工不清** | 🟡 中 |
| 4 | **沒有 VOO/QQQ 專門追蹤** | 🔴 高 |
| 5 | **沒有回測 VOO 70% + QQQ 30% 組合** | 🟡 中 |

---

## 📋 理想 DCA 結構（Jo 的需求）

### Jo 的 DCA 組合（應有的樣子）

| 倉位 | 比例 | 執行頻率 | 系統 |
|:-----|:----:|:--------:|:-----|
| **VOO** | 70% | 每月一次 | 誰管？→ ❌ 缺口 |
| **QQQ** | 30% | 每月一次 | 誰管？→ ❌ 缺口 |
| VTI（可選）| — | 每季 | 誰管？→ ❌ 缺口 |
| SCHD（可選）| 衛星 | 每季 | Sherry（有但未聚焦）|

### Jo 的 DCA 約束
```
• 不推薦個股 DCA（單一風險過高）
• VOO/VTI 任選一個當主軸，不重複
• 配息再投入，不要領出來
• 每月底檢查一次，不因下跌停止
```

---

## ✅ 改善方案

### 方案 A（推荐）：Ray 接管 VOO/QQQ，Sherry 專注 Sector 輪動

| 團隊 | 新職責 | 範圍 |
|:----:|:-------|:-----|
| **Ray** | 全球 ETF DCA（TW + US）| 0050（TW）、VOO、QQQ、VTIVTI、SCHD |
| **Sherry** | 美股 Sector 輪動 | XLK/XLF/XLE/XLV 等 |

**Ray 新增腳本：**
- `ray_us_dca_market_brief.py` — VOO/QQQ 每日追蹤
- `ray_dca_monthly_report.py` — 月度 DCA 報告（含累計成本）
- `ray_dca_sync.py` — Jo 的 DCA 執行記錄同步（手動或自動）

### 方案 B：建立獨立 Tina US DCA 系統

| 團隊 | 職責 |
|:----:|:-----|
| **Tina** | 接管 VOO 70% + QQQ 30% 追蹤 |

---

### P0（本週）

| # | 行動 | 負責 | 效果 |
|:-:|:-----|:-----|:-----|
| 1 | **Ray 加入 VOO + QQQ** 到 `dca_market_brief.py` | Tina | 追蹤 Jo 的核心倉位 |
| 2 | **刪除 Sherry 的 SPY**（改以 VOO 為核心）| Tina | 統一 Jo 的 DCA 組合 |
| 3 | **建立 `ray_us_dca.py`**（VOO/QQQ/VTI/SCHD）| Tina | 完整美股 DCA |
| 4 | **設定每月 DCA 提醒**（Tina Cron）| Tina | 解決「何時 DCA」問題 |

### P1（下週）

| # | 行動 | 效果 |
|:-:|:-----|:-----|
| 5 | **DCA 歷史累計成本追蹤**（`ray_dca_portfolio.py` 增強）| 均價/持有時間/配息再投入 |
| 6 | **回測 VOO 70% + QQQ 30% 組合**（`dca_backtest.py`）| 驗證 Jo 的 DCA 組合合理性 |
| 7 | **Tina Telegram 每月報告**（每月最後一個交易日）| 自動發送 DCA 月報 |

### P2（月度）

| # | 行動 | 效果 |
|:-:|:-----|:-----|
| 8 | **Jo 的 DCA 實際帳戶同步**（`ray_dca_sync.py`）| 讓 Tina 知道 Jo 的實際買入 |
| 9 | **配息再投入追蹤** | 了解 DCA 複利效果 |

---

## 📐 標準作業程序（SOP）— 建議版本

### 月度 DCA SOP

```
【每日】16:10（Cron: ray_dca_market_brief.py）
  → 檢查 VOO/QQQ/0050/SCHD 的 MA60偏離度 + RSI
  → 輸出：BUY x1 / HOLD x0.5 / HOLD x0
  → Telegram 摘要（如 TWII RSI > 85 → 全數 HOLD）

【每月最後一個交易日】08:00（Cron: ray_monthly_dca_report.py）
  → 發送月報到 Telegram：
    • 本月各 ETF 均價 vs 上月
    • 累計 DCA 成本（每檔持有幾筆/均價）
    • 下月建議（繼續 DCA / 加碼 / 觀望）
  → Jo 回覆「confirm」後執行（Full Think 模式）

【每季】檢視 DCA 組合
  → VOO/QQQ 是否需要 rebalance？
  → SCHD 是否仍適合？
  → 是否引進新 ETF？

【每年】年終 DCA 總檢討
  → 總回報 vs buy & hold
  → DCA 複利效果總結
  → SOUL.md 更新「實驗室規則」
```

---

## 🔧 技術缺口

| 缺口 | 嚴重性 | 說明 |
|:-----|:-------:|:-----|
| **沒有 VOO/QQQ Cron** | 🔴 | 目前這兩個完全沒被追蹤 |
| **沒有 DCA 均價追蹤** | 🟡 | 只有價格，沒有「我 DCA 了多少錢/均價多少」|
| **沒有配息追蹤** | 🟡 | DCA 的複利來自配息再投入 |
| **沒有 Telegram 月報** | 🟡 | 只有每日分析，沒有月度報告 |

---

## 🎯 Jo 的下一步

| 優先 | 行動 |
|:----:|:-----|
| P0 | 確認 Ray 接管 VOO/QQQ（+ 新 cron）？|
| P0 | 確認 Sherry 改為 Sector 輪動（XLK/XLF/XLE/XLV）？|
| P1 | 每月 DCA 提醒 Cron 設定？|

---

_報告完成 — 2026-05-08 01:00_