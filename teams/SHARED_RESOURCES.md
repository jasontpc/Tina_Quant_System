# Tina Quant System — 團隊共享資源 (Shared Resources)

所有團隊（Nana, Marcus, Ray, Tina）共享以下資源。

---

## API Tokens

### ✅ FinMind Token (已啟用)
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM"
}
```
- **用途：** 法人籌碼資料、個股/ETF日資料、融資融券
- **限制：** 300 requests/hour
- **Endpoint:** `https://api.finmindtrade.com/api/v4/data`

### ❌ Fugle Token (404，需調查)
```
00adc946-59a0-4d4e-801d-a5c05eba7278
```
- **用途：** 即時報價、技術指標
- **現況：** 所有 endpoint 回傳 404

### 📝 TWSE/TPEx OpenAPI
- 需要到官網註冊取得 Key（目前無 Key）

---

## 核心 Python 技能 (Core Skills)

| 檔案 | 功能 | 狀態 |
|:-----|:-----|:----:|
| `bandwave_system/core/finmind_institutional.py` | 法人資料抓取（個股/ETF） | ✅ 可用 |
| `bandwave_system/core/stock_names.py` | 股票名稱中文化 | ✅ 可用 |
| `bandwave_system/core/dynamic_exit.py` | ATR 停損/動態出场 | ✅ 可用 |
| `bandwave_system/core/etf_health_monitor.py` | ETF 健康度監控 | ✅ 可用 |
| `bandwave_system/core/data_fetch.py` | 資料抓取引擎 | ✅ 可用 |

---

## Ray 專用腳本 (Ray Team Scripts)

| 檔案 | 功能 |
|:-----|:-----|
| `teams/ray/ray_etf_dca.py` | ETF定期定額分析（單一標的，增強版含同類比較+建議金額）|
| `teams/ray/scripts/etf_value_screener.py` | 多ETF DCA價值篩選，輸出Top3（已就緒）|
| `teams/ray/scripts/dca_backtest.py` | DCA回測工具，52週對比Buy&Hold（已建置）|
| `teams/ray/scripts/dca_analyzer.py` | 單一ETF DCA分析（原有）|
| `teams/ray/scripts/dca_scheduler.py` | 自動化排程（原有）|

---

## 使用方法

### FinMind 法人資料
```python
from skills.stock_analyzer.bandwave_system.core.finmind_institutional import get_institutional
rows = get_institutional('00919', '2026-04-15', '2026-04-24')
```

### ETF 價格/技術指標（yfinance）
```python
import yfinance as yf
s = yf.Ticker('00919.TW')
h = s.history(period='1mo')
```

### 股票名稱
```python
from skills.stock_analyzer.bandwave_system.core.stock_names import get_name
name = get_name('3231')  # returns '緯創'
```

---

## Cron 自動化現況

| 團隊 | Cron | 狀態 |
|:-----|:-----|:----:|
| Tina API 健康檢查 | 9,13,17時(平日) | ✅ ok |
| 每日市場報告 | 8,20時 | ✅ idle |
| Nana US 盤後掃描 | 23時(平日) | ✅ idle |
| **Ray 每週DCA檢視** | 週一09:00 | ✅ 新增 |
| **Ray 每週ETF價值篩選** | 週一10:00 | ✅ 新增 |
| **Ray 每月DCA組合評估** | 每月1日10:00 | ✅ 新增 |

---

_Last Updated: 2026-04-24_
