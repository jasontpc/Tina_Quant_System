# Vogel 台指期波段團隊 — 索引文檔
> 最後更新：2026-05-07 21:10

## 正式版腳本

| 檔案 | 狀態 | 說明 |
|:-----|:----:|:-----|
| `vogel_core.py` | 主策略 | 台指期 BB 信號核心邏輯 |
| `vogel_autonomous.py` | 自主分析 | 自動分析學習系統 |
| `vogel_signals.py` | 信號追蹤 | Cron 每日台指期分析 |
| `vogel_backtest.py` | 回測 | 歷史回測系統 |
| `build_vogel_db.py` | 資料庫建構 | 資料庫建構腳本 |
| `vogel_final.py` | 最終版 | 最終整合版 |

## Cron 排程

| Job ID | 名稱 | 時間 | 腳本 |
|:-------|:-----|:-----|:-----|
| 待確認 | Vogel 台指期分析 | 平日 09:00 | `vogel_signals.py` |

## 現況

- Vogel 專注台指期 BB（布林通道）信號
- 尚未查詢到具體 cron job ID
- 主要使用 `teams/vogel/vogel_signals.py`

---
