# 🎯 團隊腳本與策略完整審查報告
**日期：** 2026-05-08 00:30
**主題：** 美股 DCA 推薦職責重疊 + 全團隊腳本與策略審查

---

## 📊 各團隊定位一覽

| 團隊 | 職責 | 當前狀態 | 腳本數 |
|:----:|:-----|:---------|------:|
| **Leo** | TW 科技股波段（2330/2454/2317/3034）| ✅ 正式運行（v6.5）| ~28 |
| **Nana** | TW 股票波段（AI/資訊/軟體）| ✅ 正式運行（v5.8）| ~40 |
| **Ray** | TW ETF DCA（0050/0056/00713）| ✅ 正式運行 | ~20 |
| **Sherry** | **TW + US ETF DCA** | ⚠️ 定位模糊 | ~8 |
| **Vogel** | 台指期波段（BB 策略）| ✅ 正常運行 | ~16 |
| **Maggy** | AI Tech 股票分析 | ✅ 正常運行 | ~20 |

---

## 🔴 重大發現：Sherry 職責衝突

### 問題

Sherry _INDEX.md 宣稱「專注美股 ETF DCA」，但 Jo 的 DCA 回覆已由 **Ray** 接管（VOO 70% + QQQ 30%）。

**Sherry 的美股 ETF 清單（已過時）：**
```
SPY, QQQ, VEA, VWO, VIG, SCHD, VYM, XLV, VHT, GLD, TLT, BND...
```

**Jo 指定的 DCA 組合：**
```
核心：VOO（70%）+ QQQ（30%）
衛星：VTI, SCHD, BND, VYM
```

兩者**完全沒有對應**。Sherry 的美股 ETF DCA 是獨立發展的，**與 Jo 的需求脫節**。

### 改善方案

**方案 A（推荐）：Sherry 專注 TW + US macro ETF**
```
職責調整：
- 擴大到全球宏觀 ETF（EEM, VWO, VEA, GLD, TLT）
- 做為 Ray 的「全球視角补充」
- 與 Ray 組成「ETF 雙团队」（TW + Global）
```

**方案 B：Sherry 專注 sector ETF 輪動**
```
職責調整：
- 关注美股 sector ETF（XLK/XLF/XLE/XLV 等）
- 根據宏觀週期做行業輪動（rotation）
- 與 Leo 的個股操作互補
```

---

## 🟡 腳本數量審查

### Leo — 28 個腳本

**問題：** 大量實驗性版本
```
leo_v123_compare.py     — 123版本比較（廢）
leo_v1v2_compare.py     — v1/v2 比較（廢）
leo_core_v2.py          — v2 核心（已被 v65 取代）
leo_autonomous_v2.py    — v2 自主（已被 v65 取代）
leo_per_stock_v2.py/v3.py — 實驗性
leo_failure_analysis.py / leo_failure_db.py — 一次性分析
leo_sim_trade.py        — 模擬交易
leo_backtest.py         — 回測工具
leo_deep_compare.py     — 比較工具
```

**建議：清理落後版本，保留：**
```
正式：leos_v65.py, leos_daily_review.py, leo_autonomous.py, leo_analysis.py
```

### Nana — ~40 個腳本

**問題：** 版本眾多（Nana v5.6/5.7/5.8 + 其他）
```
nana_v2_full.py, nana_v2_optimizer.py, nana_v2_test.py
nana_improved.py, nana_improved_v2.py
nana_system_v3.py, nana_system_v3_quick.py
nana_backtrader.py, nana_backtrader_simple.py
nana_sim_backtest.py, nana_realistic_backtest.py
nana_wfa.py — WFA 參數優化
```

**建議：Archive old，確認 Nana v5.8 是正式版**

### Vogel — 16 個腳本

**問題：** 版本洪水（v6/v7/v9/v10~v14/vfinal）
```
只保留：vogel_signals.py（cron）, vogel_core.py, vogel_autonomous.py, vogel_final.py
其餘全部 → archive/
```

---

## 📋 腳本重疊分析

| 功能 | 重疊腳本 | 建議 |
|:-----|:--------|:-----|
| DCA 回測 | `ray_dca_backtest.py`, `sherry_dca_backtest.py` | 統一到 `scripts/dca_backtest.py` |
| ETF 分析 | `ray_etf_comprehensive.py`, `sherry_autonomous.py` | 分工明確即可 |
| 市場情緒 | `ray_market_phases.py`, `sherry_autonomous.py` | 統一引用同一數據源 |
| 回測引擎 | `nana_backtrader.py`, `nana_backtrader_simple.py` | 合併或確認 one is deprecated |

---

## 🎯 美股 DCA 策略現況

### 現有腳本
- `sherry_autonomous.py` — 有完整美股 ETF 清單（SPY/QQQ/VTI/BND/TLT/GLD）
- `sherry_db.py` — ETF 基本資料（名稱/類型/追蹤指數）
- `sherry_screener.py` — ETF 篩選

### 缺口
1. **沒有 VOO**（Jo 的核心倉位）
2. **沒有 DCA 排程**（每日/每週/月定投提醒）
3. **沒有回測驗證**（VOO+QQQ 歷史表現）

---

## ✅ 改善方案（依優先級）

### P0（本週）

| # | 行動 | 負責 |
|:-:|:-----|:-----|
| 1 | **Sherry 職責確認**：確定是「全球宏觀 ETF」還是「Sector 輪動」 | Jo 確認 |
| 2 | **Vogel 版本清理**：archive/ 移走 12 個舊版（只留 4 個正式版） | Tina 執行 |
| 3 | **美股 DCA 追蹤**：Sherry 加入 VOO，追蹤 Jo 的 DCA 組合健康度 | Tina 實作 |

### P1（下週）

| # | 行動 |
|:-:|:-----|
| 4 | **Leo 版本清理**：archive/ 移走 15+ 個舊版（只保留 v65/daily/autonomous/analysis） |
| 5 | **Nana 版本確認**：確定 v5.8 是正式版，其他進 archive/ |
| 6 | **DCA 回測統一**：Ray + Sherry 共用同一 `dca_backtest.py` |

### P2（月度）

| # | 行動 |
|:-:|:-----|
| 7 | **腳本數量上限**：每團隊最多 10 個活躍腳本，超出 archive/ |
| 8 | **策略文件化**：每團隊一份 `strategy.md`（非 INDEX.md），說明核心策略邏輯 |

---

## 🎯 Jo 的下一步

1. **確認 Sherry 新職責**：全球宏觀 ETF？Sector 輪動？還是其他？
2. **確認 Vogel 清理**：刪除 12 個舊版（可隨時從 git recovery）
3. **確認美股 DCA 追蹤**：Sherry 是否要接管 Jo 的 VOO/QQQ 組合監控

---

_報告完成 — 2026-05-08 00:30_