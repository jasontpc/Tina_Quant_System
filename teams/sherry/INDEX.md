# Sherry 台股 ETF 團隊 — 索引文檔
> 最後更新：2026-05-07 21:10

## 正式版腳本

| 檔案 | 狀態 | 說明 |
|:-----|:----:|:-----|
| `sherry_autonomous.py` | 主策略 | Sherrys DCA 自主分析 |
| `sherry_cron_setup.py` | Cron 設定 | 排程設定腳本 |
| `build_sherry_db.py` | 資料庫建構 | 初始資料庫 |
| `build_sherry_backtest_db.py` | 資料庫建構 | 回測資料庫 |
| `build_sherry_sim_db.py` | 模擬交易 | 模擬交易資料庫 |

## Cron 排程

| Job ID | 名稱 | 時間 | 腳本 |
|:-------|:-----|:-----|:-----|
| 待確認 | Sherry ETF DCA 每日 | 平日 08:30 | `sherry_daily_check.py` |

## 現況

- Sherry 專注台股 ETF DCA
- 尚未查詢到具體 cron job ID
- 與 Ray 分工明確：Ray 主力，Sherry 輔助

---
