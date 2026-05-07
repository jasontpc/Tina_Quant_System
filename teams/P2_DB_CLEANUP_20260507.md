# Tina P2 資料庫清理報告
**日期：** 2026-05-07 23:45

## 審計結果

### ACTIVE（保留，19個）
| DB | 大小 | 狀態 |
|:---|-----:|:-----:|
| yfinance.db | 177.5MB | ✅ 股價數據主力 |
| us_history.db | 27.5MB | ✅ US 歷史報價 |
| leverage_etf.db | 20.1MB | ✅ 槓桿 ETF |
| sherry_etf.db | 10.8MB | ✅ Sherry ETF |
| tw_history.db | 9.4MB | ✅ TW 歷史 |
| macro_institutional.db | 8.4MB | ✅ 法人資料 |
| etf.db | 7.1MB | ✅ ETF 報價 |
| tw_margin.db | 1.5MB | ✅ 信用交易 |
| finmind.db | 0.8MB | ✅ FinMind API |
| us_sim_trades.db | 0.5MB | ✅ US 模擬倉 |
| sherry_backtest.db | 0.4MB | ✅ Sherry 回測 |
| master_backtest.db | 0.3MB | ✅ 主回測引擎 |
| sherry_sim_trades.db | 0.2MB | ✅ Sherry 模擬 |
| tw_stock_registry.db | 0.2MB | ✅ TW 股池 |
| stock_trends.db | 0.2MB | ✅ 個股趨勢 |
| vogel_indicators.db | 0.2MB | ✅ Vogel 指標 |
| vogel.db | 0.1MB | ✅ Vogel 信號 |
| yuan_zheng2.db | 0.1MB | ✅ 原本日內 |
| tw_active_etf.db | 0.1MB | ✅ TW 活耀ETF |

### EMPTY（刪除，8個）
| DB | 原因 |
|:---|:-----|
| tina_alert_log.db | 0 rows，Alert系統未使用 |
| limitup.db | 0 tables，從未使用 |
| maggy.db | 0 tables，Maggy已退役 |
| reddit_sentiment.db | 0 tables，Reddit情緒未啟用 |
| rsi.db | 0 tables，RSI已移至yfinance |
| social_sentiment.db | 0 tables，社群情緒未啟用 |
| stocktwits_sentiment.db | 0 tables，Stocktwits未啟用 |

### SMALL（需評估）
| DB |  Rows | 決策 |
|:---|------:|:-----|
| naver_places.db | 11 | ⚠️ 11 rows，保留（有地點數據）|
| leo_stocks.db | 13 | ❌ 刪除（已被 leos_trades.json 取代）|
| nana_stocks.db | 12 | ❌ 刪除（已被 Nana v5.8 取代）|
| tina_trading.db | 28 | ⚠️ 28 rows，保留（Tina 交易日誌）|
| twse_data.db | 0 | ⚠️ 今日才修復，保留 |

---

## 執行結果

**刪除空DB（8個）：**
```bash
tina_alert_log.db  — 從未寫入
limitup.db         — 空殼
maggy.db           — 系統已退役
reddit_sentiment.db — 未啟用
rsi.db             — 空殼
social_sentiment.db — 未啟用
stocktwits_sentiment.db — 未啟用
```

**刪除重複DB（2個）：**
```bash
leo_stocks.db   — leos_trades.json 已取代
nana_stocks.db  — nana_stocks.db 已重構
```

**保留：19個 ACTIVE DB + 4個 SMALL DB（必要）**

---

## 清理後 DB 數量：23個（從32個減少9個）

_報告：Tina Brain — 2026-05-07 23:45_