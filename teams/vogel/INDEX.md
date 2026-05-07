# Vogel 台指期波段團隊 — 索引文檔
> 最後更新：2026-05-07 21:25

## 正式版腳本

| 檔案 | 狀態 | 說明 |
|:-----|:----:|:-----|
| `vogel_signals.py` | ✅ 主力 | 台指期 BB 信號分析（Cron 使用）|
| `vogel_core.py` | ✅ | BB 信號核心邏輯 |
| `vogel_autonomous.py` | ✅ | 自動分析學習系統 |
| `vogel_final.py` | ✅ | 最終整合版 |
| `vogel_v10~v14.py` | 🔴 廢棄 | 版本洪水（未清理）|
| `vogel_vfinal.py` | 🔴 廢棄 | 冗餘版本 |
| `vogel_optimize.py` | 🔴 廢棄 | 實驗性 |
| `build_vogel_db.py` | 📌 | 資料庫建構（非 cron）|

## Cron 排程

| Job ID | 名稱 | 時間 | 狀態 |
|:-------|:-----|:-----|:-----:|
| `8cfc071c` | Vogel 每週波段檢討 | 週日 09:00 | 📌 idle（未到執行日）|

## 策略說明

- **BB（布林通道）策略**：以 20 日均線為中心，上下 2 標準差繪製通道
- **進場邏輯**：價格接觸下軌時做多，接觸上軌時做空（或平倉）
- **主要標的**：台指期（TXF）

## 現況

- `vogel_signals.py` 是 Cron 使用的腳本
- 16 個 .py 檔案過多，需要清理（但 cron 正常）
- 每週日 09:00 idle（需 Jo 確認是否正常）

---

## 🔴 Vogel 版本洪水清理建議

**16 個 .py → 只留 4 個：**

```
保留：
  vogel_signals.py   ← cron 調用
  vogel_core.py      ← 核心邏輯
  vogel_autonomous.py ← 自主學習
  vogel_final.py      ← 備份

移除 → archive/vogel/：
  vogel_v6.py, v7.py, v9.py, v10.py, v11.py, v12.py, v13.py, v14.py, vfinal.py
  vogel_backtest.py
  vogel_optimize.py
  build_vogel_db.py  ← 非必要
```

---

_Jo 確認後可執行清理_