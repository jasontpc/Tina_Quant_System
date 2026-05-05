# Tina 團隊分工計劃書
> 更新時間：2026-05-05 | 版本：v1.0

---

## 🎯 團隊定位

| 團隊 | 角色 | 核心任務 | 數據來源 |
|:-----|:-----|:---------|:---------|
| **Tina（大腦）** | 系統總管 / 協調者 | 健康檢查、自動化排程、跨團隊整合、RSI 資料庫維護 | yfinance / FinMind |
| **Nana（波段）** | 台股波段操作師 | 每日波段掃描（個股 RSI 35-50）、KD 黃金交叉、MA 多頭 | yfinance |
| **Leo（科技）** | AI/半導體產業分析師 | AI 科技股追蹤（2330/2454/2317/3034 等）、法人流向、產業鏈分析 | FinMind / yfinance |
| **Ray（DCA）** | ETF 長期投資者 | ETF 定額定期（DCA）、報酬/殖利率分析、長抱策略 | yfinance |
| **Sherry/Vogel** | 觀察員 | ETF 價值篩選、每週學習更新 | ETF DB |

---

## 🔄 每日流程（正常市場日）

| 時段 | 任務 | 執行者 |
|:-----|:-----|:------|
| **06:00** | RSI Backfill（補算所有缺失 RSI） | Tina（cron）|
| **07:00** | Tina 健康檢查 | Tina（cron）|
| **08:00** | Leo 光通訊每日追蹤 / Tina 歷史DB更新 / TW ETF分析 | Leo / Tina / Ray |
| **09:00** | Tina 大腦-團隊排程管理 / Tina 每日思考 / Leo 法人流向 | Tina / Leo |
| **10:00** | **Tina 全團隊整合報告**（唯一整合點） | Tina |
| **14:00** | Tina 市場情緒主動掃描 | Tina |
| **15:00** | Tina 產業研究報告 | Tina |
| **16:00** | **收盤整合** + Yahoo ETF 更新 + Nana DB 收盤更新 | Tina / Ray / Nana |
| **17:00** | Tina 每日學習更新（DB） | Tina |
| **18:00** | 社群情緒（Reddit/Tavily/StockTwits 三選一） | Tina |
| **20:00** | Tina 主動策略優化 | Tina |
| **23:00** | TW AI Tech 每日更新 | Leo |

---

## ⚠️ 禁止事項（防止衝突）

1. ❌ **同一時段同一任務只能有一個 cron job**
   - 已刪除：10:00 Leo 分析、Unified 分析（→ 保留 Tina 全團隊）
   - 已刪除：16:00 重複 5 個 → 只留 3 個（ETF + Nana + Ray）

2. ❌ **一個團隊不做另一個團隊的核心任務**
   - Ray 不做波段（由 Nana 負責）
   - Leo 不做 DCA（由 Ray 負責）
   - Tina 不做波段也不做 DCA（只做系統總管）

3. ❌ **禁止同功能腳本多版本共存**
   - Tina 大腦：只保留 `tina_brain_v3.py`（master）
   - Maggy：只保留最新穩定版本

---

## 📁 腳本存放規範

```
scripts/
├── tina_*.py          # Tina 大腦核心腳本（<= 5 個）
├── nana_*.py          # Nana 波段腳本（<= 3 個）
├── leo_*.py           # Leo 產業分析腳本（<= 5 個）
├── ray_*.py           # Ray DCA 腳本（<= 3 個）
├── closing_report.py  # 收盤報告（單一版本）
├── tw_stock_gui.py    # TW GUI 主程式
├── us_stock_gui.py    # US GUI 主程式
└── _TRASH_/           # 已刪除腳本（隔離，不在主要目錄）
```

---

## 📊 資料庫維護責任

| DB | 維護者 | 更新頻率 |
|:---|:-------|:---------|
| yfinance.db | Tina（自動） | 每日 |
| tina_master.db | Tina（RSI Backfill cron） | 每週 |
| nana_stocks.db | Nana | 每日 16:00 |
| leo_stocks.db | Leo | 每日 |
| ray_etf.db | Ray | 每日 |
| etf.db | Ray | 每日 16:00 |
| tw_history.db | Tina | 每週 |

---

## 🎯 成功指標

- Cron jobs：53 個（已整合，控制在 50-60）
- Idle jobs：< 3（盡量為 0）
- RSI DB：最新（停滯 <= 1 天）
- 腳本數量：311（目標降至 120）

---

_Last updated: 2026-05-05 17:32_