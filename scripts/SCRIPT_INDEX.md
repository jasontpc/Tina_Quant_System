# Tina 系統腳本索引

**更新時間：** 2026-05-08  
**腳本總數：** 59

---

## 📋 腳本分類索引

### 🧠 A. 大腦核心（Brain Core）⭐

| 腳本 | 功能 | 執行 |
|:-----|:-----|:-----|
| `tina_brain_core.py` | 五大層統一決策系統 | Cron 每 1h |
| `tina_integrated_monitor.py` | 整合監控（大腦+健康+五大層）| Cron 每 30m |
| `tina_brain_monitor.py` | 大腦監控 | Cron 每 30m |

### 📝 B. 記憶系統（Memory）

| 腳本 | 功能 | 執行 |
|:-----|:-----|:-----|
| `tina_memory_sync.py` | MEMORY.md 同步 | Cron AM/PM |
| `tina_decision_trigger.py` | 五大層觸發器 | 手動/測試用 |
| `tina_decision_db.py` | 決策資料庫管理 | 需重構 |

### 📰 C. 分析系統（Analysis）

| 腳本 | 功能 | 對應 Bot |
|:-----|:-----|:---------|
| `news_trends_cron.py` | News Trends 報告 | tina-reports |
| `etf_analysis_jo.py` | ETF 分析（0050/00631L/00981A）| tina-reports |
| `tw_etf_daily.py` | TW ETF 每日報告 | tina-reports |
| `hunter_scan.py` | 主動獵人成長股掃描 | tina-reports |

### 💹 D. 波段系統（Trading）

| 腳本 | 功能 | 對應 Bot |
|:-----|:-----|:---------|
| `leo_analyzer.py` | Leo 波段分析 | main |
| `leo_improved.py` | Leo 改進版 | main |
| `nana_*.py` | Nana 波段系統 | main |

### 📊 E. 回測系統（Backtest）

| 腳本 | 功能 |
|:-----|:-----|
| `tina_backtest_engine.py` | 回測引擎 |
| `tina_backtest_validator.py` | 回測驗證 |

### 🔍 F. 學習系統（Learning）

| 腳本 | 功能 |
|:-----|:-----|
| `tina_autonomous_decision.py` | 自主決策系統（需整合）|
| `tina_autonomous_learning.py` | 自主學習 |
| `tina_auto_learner.py` | 自動化學習 |
| `tina_brain_learner.py` | 大腦學習 |

### ⚙️ G. 系統維護（System）

| 腳本 | 功能 | 執行 |
|:-----|:-----|:-----|
| `tina_cron_optimizer.py` | Cron 優化器 | 手動 |
| `tina_system_sop_health.py` | SOP 健康檢查 | Cron 每日 |
| `tina_health_status_writer.py` | 健康狀態寫入 | 需合併 |
| `tina_lifecycle_monitor.py` | 生命週期監控 | 需合併 |

### 🔮 H. 未分類（Deprecated）

| 腳本 | 說明 |
|:-----|:-----|
| `tina_gui.py` | GUI 界面（未使用）|
| `tina_telegram.py` | Telegram 介面（已整合到 Gateway）|
| `tina_realtime.py` | 實時監控（功能重疊）|

---

## 📊 腳本健康度

| 類別 | 數量 | 健康度 |
|:-----|:----:|:------:|
| 大腦核心 | 3 | ⭐⭐⭐ 75% |
| 記憶系統 | 3 | ⭐⭐ 60% |
| 分析系統 | 4 | ⭐⭐⭐ 80% |
| 波段系統 | 4+ | ⭐⭐⭐ 80% |
| 回測系統 | 2 | ⭐⭐ 65% |
| 學習系統 | 5+ | ⭐ 40% |
| 系統維護 | 4 | ⭐⭐ 50% |
| 未分類 | 3+ | ⭐ 30% |

---

## 🎯 腳本整合規劃

### 需要合併（功能重疊）

| 目前腳本 | 合併到 | 原因 |
|:---------|:------|:-----|
| `tina_brain_monitor.py` | `tina_integrated_monitor.py` | 整合監控已包含 |
| `tina_lifecycle_monitor.py` | `tina_integrated_monitor.py` | 整合監控已包含 |
| `tina_health_status_writer.py` | `tina_integrated_monitor.py` | 整合監控已包含 |

### 需要重構（功能斷開）

| 腳本 | 問題 | 建議 |
|:-----|:-----|:-----|
| `tina_autonomous_decision.py` | 從未被調用 | 整合到 `tina_brain_core.py` |
| `tina_decision_db.py` | DB 為空 | 重構或刪除 |

### 需要啟用（Cron Job）

| 腳本 | 建議 |
|:-----|:-----|
| `tina_brain_core.py` | ✅ 已建立 Cron |
| `tina_integrated_monitor.py` | ✅ 已建立 Cron |
| `tina_memory_sync.py` | ✅ 已有 Cron |

---

## 📞 腳本使用指南

### 如何新增腳本

1. 命名：`{功能}_{子功能}.py`
2. 放在：`Tina_Quant_System/scripts/`
3. 更新：本索引檔案
4. 註冊：如果需要自動化，更新 `TINA_SYSTEM_SOP.md`

### 腳本執行優先順序

1. **手動測試**：`python scripts/{script}.py`
2. **Cron Job**：透過 `openclaw cron add`
3. **觸發器**：作為其他腳本的子程式

---

_Last update: 2026-05-08_
