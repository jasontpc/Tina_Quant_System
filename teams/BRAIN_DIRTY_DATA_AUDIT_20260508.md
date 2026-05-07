# Tina 大腦健康檢查 — 髒數據 / 死亡腳本 / 數據庫
**日期：** 2026-05-08 00:30
**範圍：** 全系統腳本、數據庫、數據品質審查

---

## 📊 數據庫審查

### 總覽

| 項目 | 數值 |
|:-----|-----:|
| 總 DB 數 | 28 |
| 總大小 | **266 MB** |
| 有問題 DB（有空表/small表）| 26 / 28 |
| 健康 DB | 2（etf.db, tw_stock_registry.db）|

### 🔴 應立即刪除的 DB

| DB | 大小 | 問題 |
|:---|-----:|:-----|
| `twse_data.db` | **0 MB** | 3個表全部 EMPTY（ MI_INDEX 根本沒寫入）|
| `tina_trading.db` | **0.02 MB** | 26行 RSI 數據，極小，早期實驗 |
| `macro.db` | **0 MB** | geopolitical_events/regime_classification/daily_summary 全空 |
| `vogel.db` | 0.1 MB | signals/db_version 全空 |
| `vogel_indicators.db` | 0.2 MB | signals/backtest_results/backtest 全空 |
| `vogel_tx.db` | 0.1 MB | signals 全空 |
| `naver_places.db` | 0.1 MB | products 全空（僅 places 10筆）|

### 🟡 需確認是否仍使用的 DB

| DB | 大小 | 問題 |
|:---|-----:|:-----|
| `master_backtest.db` | 0.3 MB | backtest_results EMPTY（實際數據在 trade_archive 2155筆）|
| `stock_trends.db` | 0.2 MB | stocks/trend_signals EMPTY（daily_prices 1831行可搶救）|
| `tw_margin.db` | 1.5 MB | margin_summary/margin_stats/watchlist EMPTY（margin_daily 11844行正常）|
| `sherry_etf.db` | 10.8 MB | dca_signals/dca_simulation EMPTY |
| `sherry_sim_trades.db` | 0.5 MB | trade_log/portfolio_summary EMPTY |
| `us_sim_trades.db` | 0.5 MB | trade_summary EMPTY |
| `yuan_zheng2.db` | 0.1 MB | trading_log EMPTY |
| `tw_ai_tech.db` | 0.1 MB | trade_signals/us_adp_correlation/performance/params_log 全空 |
| `us_ai_tech.db` | 0.1 MB | trade_signals/performance/params_log 全空 |

### ✅ 健康 DB（正常運作）

| DB | 大小 | 狀態 |
|:---|-----:|:-----|
| `etf.db` | 7.1 MB | etf_daily 74173行 + etf_info 90行 ✅ |
| `tw_stock_registry.db` | 0.2 MB | stock_registry 3084行 ✅ |
| `yfinance.db` | **177.5 MB** | daily_ohlcv 810449行，龐大但健康 ⚠️ 監視 |
| `leverage_etf.db` | 20.1 MB | etf_meta 22行 + daily_ohlcv 95664行 ✅ |
| `tw_history.db` | 9.4 MB | stocks 59 + daily_ohlcv 31750行 ✅ |
| `us_history.db` | 27.5 MB | daily_ohlcv 110207行 ✅ |
| `macro_institutional.db` | 8.4 MB | institutional_daily 61066行 ✅（空表是殘留）|
| `sherry_backtest.db` | 0.4 MB | dca_sim 432 + dca_monthly 2304 ✅ |
| `finmind.db` | 0.8 MB | daily_price 1931行（資料筆數偏少，需確認更新頻率）|

---

## 📜 腳本審查

### 總覽

| 項目 | 數值 |
|:-----|-----:|
| 總腳本數 | 184 |
| 髒腳本（一次性/除錯/過期）| **~91** |
| 正式腳本 | ~93 |

**⚠️ 184個腳本中，近50%是一次性除錯腳本！**

---

### 🔴 死亡腳本（應立即刪除）

| 類型 | 檔案 | 理由 |
|:-----|:-----|:-----|
| **除錯/修復腳本** | `_fix*.py` 系列（約50個）| 修完Bug後的產物，已完成任務 |
| **一次性分析** | `analyze_*.py`（2330/2454/xlv/xom）| 單次使用，無再執行必要 |
| **過期構建腳本** | `build_fugle_db.py`, `build_rsi_db.py`, `build_threads_trending_db.py` | API已更換/失效 |
| **過期版本** | `nana_v54.py`, `nana_v55.py`, `marcus_*.py` | 已被 archive 取代 |
| **過期 expand/expand** | `expand_*.py`（6個）| 數據已擴展完成 |
| **一次性爬蟲** | `naver_*.py`（3個）, `centum_*.py`（5個）, `fugle_scraper*.py` | 任務完成 |
| **單次驗證** | `test_*.py`, `verify*.py`, `check_*.py`（很多）| 除錯完成後廢棄 |
| **streamlit 備份** | `streamlit_tw_stock_v3.py.bak` | 過期備份，git已有 |
| **過期 Nana 版本** | `nana_v54.py`, `nana_v55.py`, `nana_v520.py` 等 | 已升至 v5.8 |
| **過期 Vogel 版本** | `vogel_v*.py`（v6~v14/vfinal）| 16個版本洪水 |

---

### 🟡 可保留但需檢查的腳本

| 檔案 | 問題 |
|:-----|:-----|
| `tina_health_check.py` | 有多個版本（quick/light），需統一 |
| `db_status*.py`（4個）| 多版本，確認哪個最新 |
| `update_*.py`（多個）| 確認是否仍在 cron 使用 |

---

### ✅ 正式腳本（應保留）

```
核心系統：
  streamlit_tw_stock.py         — Streamlit 主程式
  leos_v65.py / leos_daily_review.py — Leo 主力
  tina_health_check.py          — Tina 健檢（最新）
  cron_optimizer.py              — Cron 優化
  system_cron_setup.py           — Cron 設定

團隊腳本：
  teams/leadtrades/  (Leo 全套)
  teams/ray/         (Ray DCA)
  teams/sherry/      (Sherry ETF)
  teams/vogel/       (Vogel 期權)
  teams/maggy/       (Maggy AI Tech)
  teams/nana/        (Nana 波段)

公共腳本：
  scripts/ (含 daily_db_update, etf_analysis, tina_memory_sync)
```

---

## 💾 數據健康度

### 🔴 髒數據 / 死亡數據

| 項目 | 說明 |
|:-----|:-----|
| `twse_data.db`（0行）| MI_INDEX 根本沒寫入，daily_db_update.py 的 `CREATE TABLE IF NOT EXISTS` 可能寫錯table name |
| 空表眾多 | 每個 DB 幾乎都有 1-5 個 EMPTY 表（殘留 schema）|
| `sqlite_sequence` 污染 | 每個 DB 都有的內部表，沒有實際用途但干擾 audit |
| `yfinance.db` 177MB | 810449行，有些 symbol 可能已下市/重複 |

---

## ✅ 改善方案

### P0（本週）

| # | 行動 | 預期效果 |
|:-:|:-----|:---------|
| 1 | **刪除 `twse_data.db`** | 移除 0 行假數據 |
| 2 | **刪除 `tina_trading.db`** | 移除 0.02 MB 實驗品 |
| 3 | **刪除 `macro.db`** | 移除空 DB |
| 4 | **刪除 3 個空 vogel*.db** | 移除信號記錄為空的 DB |
| 5 | **刪除 50+ 個 `_fix*.py` / `check_*.py`** | 清除除錯腳本 |
| 6 | **刪除 `naver_*.py` / `centum_*.py`** | 清除一次性爬蟲 |
| 7 | **刪除 `analyze_*.py`（4個）** | 清除單次分析 |
| 8 | **刪除過期版本：`nana_v54/v55`, `marcus_*`, `v421/v423/v424`** | 清除過期版本 |
| 9 | **刪除 `streamlit_tw_stock_v3.py.bak`** | 清除過期備份 |
| 10 | **修復 `twse_data.db` 空表問題**（或確認是否需要）| 確認 MI_INDEX 是否需要 |

### P1（下週）

| # | 行動 |
|:-:|:-----|
| 11 | 統一 `tina_health_check.py`（3版本→1） |
| 12 | 統一 `db_status*.py`（4版本→1） |
| 13 | 對 `yfinance.db` 做去重（移除已下市 symbol）|
| 14 | 每個 DB 的 `sqlite_sequence` 表移除干擾（audit時自動忽略）|

### P2（月度）

| # | 行動 |
|:-:|:-----|
| 15 | 腳本數量上限：每團隊目錄不超過 20 個 .py |
| 16 | 建立 `_archive/` 目錄，移入非活躍腳本（而非刪除）|

---

## ⚡ 快速清理指令

```bash
# 刪除髒腳本（一次性）
Remove-Item *_fix*.py, analyze_*.py, check_*.py, verify*.py, test_*.py, naver_*.py, centum_*.py, fugle_*.py, expand_*.py, build_fugle_db.py, build_rsi_db.py, build_threads_trending_db.py, marcus_*.py, nana_v54.py, nana_v55.py, v421_*.py, v423_*.py, v424_*.py, continue_us_history.py, sel_test.py, try_api*.py, final_*.py, fill_*.py, rebuild_*.py -ErrorAction SilentlyContinue

# 刪除髒 DB
Remove-Item twse_data.db, tina_trading.db, macro.db, naver_places.db -ErrorAction SilentlyContinue

# 刪除過期備份
Remove-Item streamlit_tw_stock_v3.py.bak -ErrorAction SilentlyContinue
```

---

## 📊 預期清理效果

| 項目 | 清理前 | 清理後 |
|:-----|-------:|-------:|
| 腳本數 | 184 | ~110（-40%）|
| DB 數 | 28 | ~22（-21%）|
| 總大小 | 266 MB | ~240 MB（-10%）|
| 空 DB | 7 | 0 |

---

_報告完成 — 2026-05-08 00:30_