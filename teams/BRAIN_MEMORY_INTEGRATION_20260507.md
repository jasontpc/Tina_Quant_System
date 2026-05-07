# Tina 大腦記憶系統 — 整合審查與改善方案
**日期：** 2026-05-07 23:20
**目標：** 審查記憶系統、整合資料庫、建立永續機制

---

## 📊 現況診斷

### 資料庫地圖

| 資料庫 | 大小 | 用途 | 狀態 |
|:-------|-----:|:-----|:-----|
| yfinance.db | 177.5MB | US 股價 | ✅ 活躍 |
| etf.db | 7.1MB | TW ETF | ✅ 活躍 |
| finmind.db | 0.8MB | 法人資料 | ✅ 活躍 |
| us_sim_trades.db | 0.5MB | US 模擬倉 | ⚠️ 需整合 |
| sherry_sim_trades.db | 0.2MB | Sherry 模擬 | ⚠️ 需整合 |
| master_backtest.db | 0.3MB | 回測結果 | ⚠️ 需整合 |
| leo_stocks.db | 0.0MB | Leo 信號 | 🔴 空白 |
| nana_stocks.db | 0.0MB | Nana 信號 | 🔴 空白 |
| experience_ledger.json | 0.0MB | 經驗簿 | 🔴 **僅12筆** |
| tina_xp.db | 0.0MB | XP 系統 | 🔴 未啟用 |

### 記憶系統結構

| 系統 | 現況 | 評估 |
|:-----|:-----|:-----|
| 每日記憶（memory/*.md）| 57個日誌檔 | ⚠️ 未蒸餾 |
| 長期記憶（MEMORY.md）| 200行，過時 | 🔴 需更新 |
| 經驗簿（experience_ledger.json）| **12筆**（太少）| 🔴 幾近空白 |
| 冷熱溫度（hot/cold/warm）| 有結構但閒置 | 🟡 未啟用 |
| 教訓系統（lessons/wins/losses）| **兩個資料夾全是空的** | 🔴 從未使用 |
| 投資組合（portfolio/decisions）| 幾乎空白 | 🔴 從未使用 |
| 每週回顧 Cron | **不存在** | 🔴 需建立 |

---

## 🔴 核心問題

### 問題 1：記憶系統孤島化

**症狀：**
- 每日記憶（57個檔案）累積但**從未蒸餾**
- MEMORY.md 最後更新是 2026-05-03
- `tina_weekly_reflection.py` 存在但**從未執行**
- 每週日 10:00 的 Cron Job **根本不存在**

**根本原因：**
- 有流程（`tina_weekly_reflection.py`）但沒有觸發器（Cron）
- 沒有將每日經驗寫入 `experience_ledger.json` 的機制
- 各團隊（Leo/Nana/Ray）各自為政，沒有共享學習

---

### 問題 2：experience_ledger 形同虛設

**現實：**
```
experience_ledger.json: 12 筆
- AAPL、MSFT、YANG、5269.TW 等各 1 筆
- 2382 廣達（5/7 賣出）：直到今天才手動寫入
- Leo 的 19 筆倉位：0 筆寫入
- Nana 的交易記錄：0 筆
```

**根本原因：**
- `experience_ledger.json` 沒有被任何腳本自動寫入
- `tina_weekly_reflection.py` 有寫入邏輯但沒有 Cron
- 各團隊沒有整合到統一經驗系統

---

### 問題 3：Lessons 系統從未啟用

**現實：**
```
lessons/wins/  →  空的（0 個檔案）
lessons/losses/ →  空的（0 個檔案）
portfolio/decisions/ →  幾乎空白
```

**根本原因：**
- 沒有從 `experience_ledger.json` 蒸餾到 lessons 的流程
- 沒有將成功/失敗案例寫入結構化檔案的機制

---

## ✅ 改善方案

### 方案 A：建立每週蒸餾 Cron（P0）

**立即執行：** 建立 Cron Job 觸發 `tina_weekly_reflection.py`

```
排程：每週日 10:00
超時：300s
腳本：python tina_weekly_reflection.py
```

**蒸餾流程（每週日自動執行）：**
```
memory/2026-05-03.md
memory/2026-05-04.md
...           ↓
          讀取本週所有日誌
               ↓
          識別重大決策（Leo/Nana/Ray）
               ↓
          比對 experience_ledger
               ↓
          蒸餾：寫入 lessons/wins/ 或 lessons/losses/
               ↓
          更新 MEMORY.md（每週原則更新）
               ↓
          Telegram 推送本週摘要
```

---

### 方案 B：整合各團隊到統一經驗系統（P1）

**Leo → experience_ledger：**
```python
# 在 leos_daily_review.py 的平倉邏輯中加入：
if PAPER_TRADER:
    PAPER_TRADER.sync_from_leo(trade_key, ...)

# 在 tina_weekly_reflection.py 中自動蒸餾到 lessons/
```

**Nana → experience_ledger：**
```python
# nana_v5.py 的平倉時寫入 ledger
```

**Ray → experience_ledger：**
```python
# dca_market_brief.py 的信號寫入 ledger
```

---

### 方案 C：MEMORY.md 自動更新（P1）

每次蒸餾後，自動更新 MEMORY.md 的關鍵區段：
- 持倉狀態
- 本週重大錯誤
- 策略調整
- 新學到的教訓

---

## 🛠️ 立即行動清單

| 優先 | 行動 | 檔案 |
|:----:|:-----|:-----|
| P0 | 建立每週日 10:00 Cron：`tina_weekly_reflection.py` | OpenClaw |
| P0 | 補填 2382 lesson 到 experience_ledger | 已完成 |
| P0 | 補填 Leo 19 筆交易 lesson | `le*_trades.json` → ledger |
| P1 | 將 `tina_weekly_reflection.py` 整合進 Tina 健康檢查 | `tina_health_check.py` |
| P1 | 建立 Lessons 寫入邏輯（wins/losses）| `tina_weekly_reflection.py` |
| P2 | 清理 32 個 DB 中的閒置資料庫 | 待評估 |
| P2 | 整合 Nana/Ray 到 experience_ledger | `nana_v5.py` / `dca_market_brief.py` |

---

## 📐 整合後的記憶系統架構

```
┌─────────────────────────────────────────────┐
│              每日 Cron Jobs                    │
│  Leo每日 / Nana波段 / Ray DCA / ETF分析        │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  memory/YYYY-MM-DD  │  ← 原始日誌
         └─────────┬──────────┘
                   │  每週日 10:00
         ┌─────────▼──────────┐
         │ tina_weekly_reflection │  ← 蒸餾引擎
         └─────────┬──────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
 experience_   lessons/       MEMORY.md
 ledger.json   wins/losses    （長期原則）
    │          portfolio/
    │          decisions/
    │
    ▼
 TinaBrain
 (進場前自動查詢)
```

---

## 🎯 承諾

| 時間 | 行動 |
|:-----|:-----|
| 今晚 | 建立每週日 10:00 Cron |
| 今晚 | 補填 Leo 19 筆交易到 experience_ledger |
| 明天 | 執行第一次 `tina_weekly_reflection.py` |
| 本週 | 將 Nana/Ray 整合到統一經驗系統 |

---

_報告：Tina Brain v3 — 2026-05-07 23:20_