# Leo 系統腳本索引 — 2026-04-27 06:27

## 腳本分類索引

### 🏆 正式版本（Production）
| 腳本 | 功能 | 版本 |
|------|------|------|
| `leo_backtest.py` | 歷史回測系統 | v7.0 |
| `leo_per_stock_params_vOfficial.json` | 正式版參數 | vOfficial |

### 🔄 自動化排程腳本
| 腳本 | 功能 | Cron 排程 |
|------|------|----------|
| `leo_per_stock_trade.py` | 個股參數分析 | 每週三 09:00 |
| `leo_failure_db.py` | 失敗數據庫分析 | 每週日 06:00 |
| `leo_version_tracker.py` | 版本追蹤分析 | 每週日 07:00 |
| `leo_autonomous_optimizer.py` | 自主學習優化 | 每週日 04:00 |

### 📊 分析腳本
| 腳本 | 功能 |
|------|------|
| `leo_core_analysis.py` | 核心波段系統分析 |
| `leo_deep_compare.py` | 失敗 vs 全量數據對比 |
| `leo_rsi_analysis.py` | RSI 區間深度分析 |
| `leo_v123_compare.py` | v1/v2/v3 版本對比 |
| `leo_v1v2_compare.py` | v1 vs v2 對比 |
| `leo_version_tracker.py` | 版本歷史追蹤 |

### ⚠️ 廢棄腳本（勿用）
| 腳本 | 原因 |
|------|------|
| `leo_per_stock_v2.py` | 邏輯錯誤（RSI<35結論相反）|
| `leo_per_stock_v3.py` | 修正錯誤的嘗試 |
| `leo_vfinal.py` | 擴大RSI範圍導致勝率下降 |
| `leo_core_v2.py` | 動量過濾過嚴，效果變差 |

### 📁 資料庫檔案
| 檔案 | 說明 |
|------|------|
| `leo_failure_db.json` | 失敗交易資料庫（15筆）|
| `leo_failure_analysis_report.json` | 失敗分析報告 |
| `leo_version_history.json` | 版本歷史資料庫 |
| `leo_per_stock_params_vOfficial.json` | 正式版參數 |
| `leo_per_stock_params.json` | 原始個股參數 |
| `leos_backtest_report.csv` | 回測報告 |

---

## 改善策略排程建議

| 優先級 | 任務 | 腳本 | 頻率 |
|:------:|------|------|------|
| 🔴 HIGH | 每日市場掃描 | `leo_per_stock_trade.py` | 每日 |
| 🔴 HIGH | 失敗數據庫更新 | `leo_failure_db.py` | 每週 |
| 🔴 HIGH | 版本追蹤分析 | `leo_version_tracker.py` | 每週 |
| 🟡 MEDIUM | 自主學習優化 | `leo_autonomous_optimizer.py` | 每週 |
| 🟡 MEDIUM | 歷史回測驗證 | `leo_backtest.py` | 每週 |

---

## 核心改善規則（未來依據）

1. **RULE_001**: RSI 進場閾值維持 40-55
2. **RULE_002**: 避免擴大 RSI 進場範圍（不要 < 30）
3. **RULE_003**: 持有天數維持 30-45 天
4. **RULE_004**: TP 5-8%，SL 8-10%，TP/SL > 2.0
5. **RULE_005**: 移除弱勢股可提升整體勝率
6. **RULE_006**: 失敗數據庫需 > 50 筆才具統計顯著性
7. **RULE_007**: 全量數據分析優先於失敗數據分析
8. **RULE_008**: 避免大幅修改已驗證的有效參數

---

## Cron Job 優化建議

| 目前排程 | 建議優化 |
|---------|---------|
| `0 9 * * 3` | ✅ 維持（個股參數分析）|
| `0 6 * * 0` | ✅ 維持（失敗數據庫）|
| 新增 `0 7 * * 0` | 版本追蹤分析（每週日）|
| `0 4 * * 0` | ✅ 維持（自主學習）|

---

## 腳本執行優先順序

1. `leo_per_stock_trade.py` — 每日市場掃描（最高優先）
2. `leo_failure_db.py` — 每週失敗分析
3. `leo_version_tracker.py` — 每週版本追蹤
4. `leo_autonomous_optimizer.py` — 每週自主學習

---

**最後更新：2026-04-27 06:27**