# Maggy 美股波段團隊 — 索引文檔
> 最後更新：2026-05-07 21:10

## 正式版腳本

| 檔案 | 狀態 | 說明 |
|:-----|:----:|:-----|
| `build_maggy_db.py` | 資料庫建構 | 初始資料庫構建 |
| `build_maggy_db_extended.py` | 資料庫建構 | 擴展版資料庫 |
| `build_maggy_ai_tech_db.py` | 資料庫建構 | AI/科技股專用資料庫 |
| `build_maggy_rsi_db.py` | 資料庫建構 | RSI 資料庫 |
| `maggy_advanced_strategies.py` | 分析 | 進階策略分析 |

## 資料庫

| 檔案 | 用途 | 備註 |
|:-----|:-----|:-----|
| `yfinance.db` | 實際寫入位置 | `maggy_db_update.py` 寫入此檔 |
| `maggy.db` | 0 bytes 空殼 | 已廢棄，不使用 |

## Cron 排程

| Job ID | 名稱 | 時間 | 腳本 |
|:-------|:-----|:-----|:-----|
| 現有 cron | Maggy AI 策略每日 | 08:00 | `maggy_ai_strategy.py` |
| 現有 cron | Maggy 美股收盤 | 15:00 | `maggy_daily_check.py` |
| 現有 cron | Maggy 每週波段報告 | 週日 10:00 | `maggy_backtest.py` |

## 現況

- `maggy.db` 為 0 bytes 空殼（從未使用）
- 實際資料寫入 `yfinance.db`（由 `teams/maggy/maggy_db_update.py` 管理）
- `system_status.py` 已修復，不再對空殼 `maggy.db` 報錯

---
