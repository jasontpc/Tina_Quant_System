# Sherry 台股 ETF 團隊 — 索引文檔
> 最後更新：2026-05-07 21:25

## 正式版腳本

| 檔案 | 狀態 | 說明 |
|:-----|:----:|:-----|
| `scripts/sherry_autonomous.py` | ✅ 主力 | 自主學習 + ETF 分析 |
| `scripts/sherry_daily_check.py` | ✅ 主力 | DCA 每日檢查 |
| `scripts/sherry_screener.py` | ✅ | ETF 篩選 |
| `scripts/sherry_cron_setup.py` | ✅ | Cron 設定 |

## Cron 排程（已確認）

| Job ID | 名稱 | 時間 | 腳本 | 狀態 |
|:-------|:-----|:-----|:-----|:-----:|
| `885a72fa` | Sherry ETF DCA 每日檢查 | 平日 08:00 | `sherry_daily_check.py` | ✅ ok（14h前）|
| `85b3eee5` | Sherry 每週 ETF 總檢討 | 週日 09:00 | ? | 📌 idle（需確認腳本）|

## 觀察名單（美股 ETF）

| 代號 | 名稱 | 用途 |
|:-----|:-----|:-----|
| SPY | S&P 500 | 核心 |
| QQQ | Nasdaq | 衛星 |
| VEA | 發達市場 | 分散 |
| GLD | 黃金 | 避險 |
| TLT | 長債 | 避險 |
| BND | 綜合債券 | 穩健 |

## 現況

- Sherry 專注美股 ETF DCA，與 Ray 的台股 ETF DCA 分工明確
- Cron 已設定每日 08:00（工作日）✅
- 每週日 09:00 idle（需確認腳本是否存在）

---