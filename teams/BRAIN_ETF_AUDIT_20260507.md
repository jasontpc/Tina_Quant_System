# Tina 大腦健檢 — ETF 分析腳本審查報告
**日期：** 2026-05-07 22:50
**對話上下文：** Jo 展示了 ETF 報酬分析報告（含 VEA/BND/00713）
**目標：** 審查腳本、建立 SOP、排程建議

---

## 📋 腳本識別

**腳本源頭（推測）：**

報告格式與 `teams/ray/ray_etf_comprehensive.py` 相似，但即時數據顯示差異：
- VEA RSI 54.8 / BND RSI 44 → 代表使用 **yfinance 即時計算**，非 DB
- 「6M報酬」欄位 → 存在於 `ray_etf_comprehensive.py`
- Score 系統（0-10）→ 自定義系統

**確認的分析腳本：**
```
scripts/etf_recommendation.py    ← 有語法錯誤，無法執行
teams/ray/ray_etf_comprehensive.py  ← 綜合分析，但無 cron
```

---

## 🔴 問題診斷

### 問題 1：etf_recommendation.py 無法執行

| 問題 | 位置 | 嚴重度 |
|:-----|:-----|:-------:|
| 語法錯誤：`str(ETF_DB))` 雙括號 | Line 9 | 🔴 P0 |
| `daily_ohlcv` table 不存在於 etf.db | Line 14 | 🔴 P0 |
| TW ETF `.TW` suffix 錯誤 | Line 47 | 🔴 P0 |
| US ETF 只 11 檔（太少）| Line 25 | 🟡 P1 |
| 無 6M 報酬計算 | 整個腳本 | 🟡 P1 |
| Score 系統錯誤（RSI<40=+40分不合理）| Line 93 | 🔴 P1 |
| 硬編碼持有：`00713.TW $52.85` | Line 135 | 🟡 P2 |
| **無 cron job** | 整個腳本 | 🔴 P0 |
| **無 Telegram push** | 整個腳本 | 🔴 P0 |

### 問題 2：ray_etf_comprehensive.py 自動化不足

| 問題 | 嚴重度 |
|:-----|:-------:|
| 無 cron job（手動執行）| 🔴 P0 |
| 無 Telegram push | 🔴 P0 |
| TW ETF 只 15 檔（少了 00981A 等）| 🟡 P1 |
| US ETF 完全沒有覆蓋 | 🔴 P0 |
| 硬編碼 holdings（底部）| 🟡 P2 |
| Score 系統不透明 | 🟡 P2 |

---

## 📊 Jo 的報告解讀

```
✅ 建議進場（高Score）
| ETF   | 價格     | RSI  | Score | 6M報酬   |
| ----- | ------ | ---- | ----- | ------ |
| VEA   | $70.61 | 54.8 | 10    | +17.2% |
| BND   | $73.57 | 44.0 | 10    | +1.0%  |
| 00713 | $54.30 | 59.2 | 7     | 觀望     |
```

**分析：**
- VEA：RSI 54.8（健康區間）+ Score 10 + 6M +17.2% → 強烈建議
- BND：RSI 44（超賣）+ Score 10 + 6M +1.0% → 保守建議
- 00713：RSI 59.2（中性）+ Score 7 → 觀望

**這個腳本輸出是「及時市場掃描」，並非 cron 自動化產出。**

---

## 🛠️ 改善方案

### 方案 A：整合進 Streamlit（TW/US 批次分析旁邊）

**優點：** 共用 UI、直接 Telegram push
**缺點：** Streamlit 需要一直開著

### 方案 B：獨立 `etf_analysis.py` + cron

**優點：** 獨立運行、可定時、Telegram push
**缺點：** 需要新 cron job

**建議採用方案 B**（因為 Streamlit 只是視覺介面，不應承擔分析職責）

---

## 📐 標準作業程序（SOP）

### ETF 分析腳本標準

```python
"""
ETF 分析腳本標準 v1.0
========================
職責：每日自動分析 TW + US ETF，輸出建議並推送到 Telegram
Cron：每日 16:30（TW 收盤後）
"""

# 標準輸入
ETF_LIST_TW = ['0050', '0056', '00646', '00662', '00713', '00757', '00919', '00927', '00981A']
ETF_LIST_US = ['VTI', 'VEA', 'BND', 'SCHD', 'SPY', 'QQQ']

# 標準評分
SCORE_RSI_LOW   = 30   # RSI < 50 → 進場區間
SCORE_RSI_HIGH  = 0     # RSI > 70 → 觀望
SCORE_MACD_POS  = 20   # MACD > 0
SCORE_MA_BULL  = 15   # MA20 > MA60
SCORE_RETURN_6M = 25   # 6M 報酬 > 15%

# 評估閾值
BUY_THRESHOLD  = 60   # Score >= 60 → 建議進場
WATCH_THRESHOLD = 40   # Score >= 40 → 觀望
REJECT_THRESHOLD = 0    # Score < 40 → 不建議

# 標準輸出格式
REPORT_TEMPLATE = """
📊 ETF 報酬/殖利率/EPS 分析結果 ({time})
✅ 建議進場（高Score）
| ETF | 價格 | RSI | Score | 6M報酬 |
|:----|:-----:|:---:|:-----:|:-------:|
{rows}

⚠️ 過熱觀望（RSI > 70）
{overbought_list}

🏆 最高報酬策略排名
{top_ranking}
"""
```

### 標準報告格式

```
📊 ETF 分析報告 — 2026-05-07 16:30

✅ 建議進場
| ETF   | 價格     | RSI | Score | 6M報酬 |
|:-----|---------:|---:|------:|-------:|
| VEA  | $70.61  | 55 | 10    | +17.2% |
| BND  | $73.57  | 44 | 10    | +1.0%  |

⚠️ 過熱觀望（RSI > 70）
VTI、VOO、0050、0056、00646、QQQ

🏆 最佳進場：VEA（RSI 54.8，黃金區間）
```

---

## ⏰ 排程建議

| 時間 | 腳本 | 頻率 | 職責 |
|:-----|:-----|:-----|:-----|
| 16:30 | `etf_analysis.py` | 每日 | TW/US ETF 即時分析 + Telegram |
| 22:00 | `etf_analysis.py --quick` | 每日 | US 開盤後複檢 |
| 週日 10:00 | `ray_etf_comprehensive.py` | 每週 | 深度 CP 值分析 |

---

## 📋 立即行動清單

| 優先 | 行動 | 負責 |
|:----:|:-----|:-----|
| P0 | 修復 `scripts/etf_recommendation.py` 語法錯誤 | Tina |
| P0 | 為 `etf_analysis.py` 加上 cron（每日 16:30）| Tina |
| P0 | 加入 Telegram push 功能 | Tina |
| P1 | 統一 Score 系統（採用標準閾值）| Tina |
| P1 | 加入 US ETF（NASDAQ-100）| Tina |
| P2 | 移除硬編碼 holdings | Tina |
| P2 | 建立 `data/etf_signals.json` 寫入機制 | Tina |

---

## 💡 長期建議

1. **合併腳本職責**：Streamlit 只負責 UI，分析全部移到 cron
2. **統一是市場**：所有分析腳本（TW/US/個股）統一使用 `data/market_signals.json`
3. **Telegram 是骨幹**：所有重要報告都應該直接推送到 Telegram

---

_報告：Tina Brain v3 — 2026-05-07 22:50_