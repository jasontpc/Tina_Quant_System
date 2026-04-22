# Tina 運維開發聯隊 - 工作索引表

## 📅 日期: 2026-04-22

---

## 1️⃣ 系統索引表

```
Tina_Quant_System/
├── core/              核心系統 (tina_system.py, monitor_rules.json)
├── api/               API整合 (api_gateway.py, twse_api_complete.py)
├── strategies/        策略模組
├── backtest/          回測系統 (v3_12_top50.py, loss_pattern_analysis.py)
├── data/              資料庫 (tina_master.db, watchlist.json, loss_rules.json)
├── archive/           歸檔資料夾
├── README.md          系統文檔
├── TEAM.md            團隊手冊
├── WORK_INDEX.md      工作索引表
└── GITHUB_SETUP.md    GitHub指南
```

---

## 2️⃣ 團隊分工表

| 角色 | 核心任務 |
|:-----|:---------|
| **Architect** | 系統設計、任務分配、協調 |
| **Quant Developer** | v3.13策略開發、參數優化 |
| **Debugger** | API錯誤分析、邏輯Bug修復 |
| **SRE** | Git備份、檔案歸檔、API健康檢查 |
| **Backtester** | 專業回測、壓力測試、生成報告 |

---

## 3️⃣ 自動化排程

| 時間 | 負責 | 任務 |
|:-----|:-----|:-----|
| 每日 16:30 | Quant Developer | 策略迭代、v3.13 draft |
| 每日 23:00 | SRE | 健康巡檢、Git備份、檔案歸檔 |
| 每週六 10:00 | Backtester | 深度壓力回測、網格搜索 |

---

## 4️⃣ 當前任務

| 協議 | 內容 | 狀態 |
|:----:|:-----|:-----:|
| 2 | 壓力測試 (500點大跌) | 🔄 執行中 |
| 3 | 參數敏感度分析 | 🔄 執行中 |
| 4 | 交易成本與滑價模擬 | 🔄 執行中 |

---

## 5️⃣ v3.12 回測效能

| 指標 | 目標 | 目前 |
|:-----|:----:|:-----:|
| 勝率 | >65% | 58.7% |
| Profit Factor | >1.5 | ~1.9 ✅ |
| 平均報酬 | >3% | +10.34% ✅ |