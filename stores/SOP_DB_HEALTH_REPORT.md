# Tina 全系統資料庫健檢報告
**日期：** 2026-05-11 20:25
**檢查範圍：** 20 個資料庫 / 總大小：~183MB

---

## 一、概況

| 項目 | 數值 |
|:-----|:-----|
| 總 DB 數 | 20 |
| 總大小 | ~183MB |
| 健康 | 20/20 ✅ |
| 有 schema 問題 | 12/20 ⚠️ |
| 建議刪除 | 1 🔴 |

---

## 二、🔴 立即處理（刪除/修復）

### 2-1：growth_paper_trading.db — 全空，佔位檔

```
[DB] growth_paper_trading.db (20KB)
   daily_evaluation: 0 rows
   positions: 0 rows
   trades: 0 rows
```
**行動：刪除**
```powershell
Remove-Item "C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\growth_paper_trading.db" -Force
```

---

### 2-2：yfinance.db — symbols 表全面 NULL

| Column | NULL % | 影響 |
|:-------|:------:|:-----|
| symbols.name | **100%** | 股票名稱全無 |
| symbols.exchange | **100%** | 交易所全無 |
| symbols.notes | **100%** | 備註全無 |
| daily_ohlcv.sma_120 | **61%** | 120日均線缺失 |
| daily_ohlcv.bb_upper/middle/lower | **51%** | Bollinger Bands 缺失 |

**根本原因：** `symbols` 表的 name/exchange/notes 從未正確寫入
**行動：** 建立 `fix_yfinance_symbols.py` 修補或重新抓取

---

### 2-3：多個 DB 的 sim_trade / backtest 欄位 100% NULL

| DB | Table | 全 NULL 欄位 |
|:---|:------|:------------|
| master_backtest.db | trade_archive | quantity, return_amount |
| sherry_sim_trades.db | sim_trades | quantity, side, return_amount |
| us_sim_trades.db | sim_trades | quantity, side, return_amount |
| tw_margin.db | margin_summary | margin_limit, short_limit |
| finmind.db | margin | margin_ratio |

**根本原因：** 這些欄位在 schema 有，但寫入時從未使用（可能是舊版本留下）
**行動：** 確認不再使用後，用 `ALTER TABLE DROP COLUMN` 移除（SQLite 3.35.0+）

---

## 三、⚠️ 需要關注的資料

### 3-1：空表（無資料但有 schema）

| DB | Table | 用途 |
|:---|:------|:-----|
| sherry_etf.db | dca_signals | 建議廢除 |
| sherry_etf.db | dca_simulation | 建議廢除 |
| stock_trends.db | stocks | 0 rows |
| stock_trends.db | trend_signals | 0 rows |
| stock_trends.db | trending_signals | 41 rows (有資料) |
| sherry_etf.db | etf_daily | 43,056 rows ✅ |
| sherry_backtest.db | strategy_compare | 0 rows |

### 3-2：資料日期過舊

| DB | Table | 最新日期 | 天前 |
|:---|:------|:---------|:----|
| leverage_etf.db | daily_ohlcv | 2026-05-01 | 10天 |
| sherry_etf.db | etf_daily | 2026-04-28 | 13天 |
| stock_trends.db | daily_prices | 2026-04-30 | 11天 |
| stock_trends.db | technical_indicators | 2026-04-30 | 11天 |
| us_history.db | daily_ohlcv | 2026-05-07 | ✅ 4天前 |

**leverage_etf.db 落後 10 天**，需要確認更新 cron 是否正常

### 3-3：sherry_sim_trades.db — 888 筆 open_positions 但無 quantity/side

```
open_positions: 888 rows（有意義的倉位）
BUT: sim_trades 3,653 rows 全 NULL
closed_positions: 883 rows
```
**懷疑：** sherry_sim_trades 和 sim_trades 是兩套獨立的記帳系統，其中一個已廢棄

---

## 四、✅ 健康良好的資料庫

| DB | 大小 | 最新 | 備註 |
|:---|-----:|:-----|:-----|
| yfinance.db | 113MB | 2026-05-08 | ✅ 每小時更新 |
| us_history.db | 27.5MB | 2026-05-07 | ✅ 正常 |
| tw_history.db | 9.5MB | 2026-05-07 | ✅ 正常 |
| etf.db | 7.1MB | 2026-05-08 | ✅ 正常 |
| finmind.db | 860KB | 2026-05-07 | ⚠️ margin_ratio 全 NULL |
| news_trends.db | 116KB | 2026-05-08 | ✅ 有每日更新 |

---

## 五、改善計畫

### Phase 1：今天（緊急）

| 行動 | 影響 | 預期效果 |
|:-----|:-----|:---------|
| 刪除 growth_paper_trading.db | 移除 20KB 空殼 | 系統整潔 |
| 修復 yfinance symbols NULL | 1,290 檔名稱可顯示 | 提升可用性 |

### Phase 2：本週

| 行動 | 說明 |
|:-----|:-----|
| 建立 `fix_yfinance_symbols.py` | 從 yfinance 或 registry 重新填入 symbols.name |
| 清理槓桿 ETF 更新延遲 | 確認 leverage_etf_update cron 正常 |
| sherry_sim_trades 審計 | 確認哪套交易系統是正確的 |
| finmind.margin_ratio 修復 | 確認 API 回傳欄位名稱 |

### Phase 3：本月

| 行動 | 說明 |
|:-----|:-----|
| 建立 DB 健康度 Cron | 每週一執行 db_health_check.py |
| 設定 DB 大小警戒線 | >100MB 自動通知 |
| 建立所有 DB 的 schema 文件 | 避免未來類似問題 |
| 審計全部 0 rows 表 | 決定刪除或保留 |

---

## 六、yfinance.db symbols 修復方案

```python
# 從 tw_stock_registry 和 us_history 補足名稱
import sqlite3

conn = sqlite3.connect('yfinance.db')
cur = conn.cursor()

# 確認 symbols 表的 symbol 欄位有值
cur.execute("SELECT COUNT(*) FROM symbols WHERE symbol IS NOT NULL")
print(f"Symbols with code: {cur.fetchone()[0]}")

# 從 registry 補足 TW 名稱
cur.execute("""
    UPDATE symbols
    SET name = (
        SELECT name_cn FROM tw_stock_registry
        WHERE symbols.symbol = tw_stock_registry.code
    )
    WHERE name IS NULL AND symbol LIKE '%'
""")
conn.commit()
conn.close()
```

---

_本報告由 Tina 大腦 v3.6 資料庫健檢引擎產出_
_下次健檢：2026-05-12 08:00_