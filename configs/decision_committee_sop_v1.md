# Tina 決策委員會 — 慢思考 SOP 重整計畫
**日期：2026-05-09 | 版本：v1.0**
**角色：Tina 分析師（Tina-Macro）主導**

---

## 目標

將系統內 180+ 支腳本整合為三大分類：**波段交易**、**DCA**、**ETF**，並建立「決策委員會慢思考」標準作業流程，開發台美股長期持有成長股策略，附模擬交易與歷史回測。

---

## 一、腳本三大分類地圖

### 📊 分類 A：波段交易（Short-term Swing）

**職責**：個股短線進場（5-10天），RSI 均值回歸為核心邏輯

**核心腳本：**
| 腳本 | 功能 |
|------|------|
| `stock_strategy_executor.py` | 讀取策略配置、檢查進場/出場條件、產出訊號 |
| `tw_growth_screener_unlimited.py` | 台股成長股三層篩選（基礎→基本面→技術面），股價<100 |
| `us_value_growth_screener.py` | 美股價值成長股三層過濾，股價<$100 |
| `tina_backtest_engine.py` | 本地 DB 波段回測引擎（RSI<35 進場，-8%停損） |
| `tina_paper_trading.py` | 模擬交易引擎 |
| `stock_strategy_tracker.py` | 個股策略追蹤與日誌 |
| `tina_reasoning_engine.py` | 波段推理引擎（結合總經數據） |
| `hunter_scan.py` | 短線獵人掃描 |
| `dynamic_rsi_scanner.py` | 動態 RSI 掃描器 |
| `guard_market_scanner.py` | 市場警示掃描 |

**已驗證參數（unified_strategy_config.json）：**
- RSI 進場：< 55（normal）、< 45（strict）
- 停損：2.0x ATR 或 -8%
- 停利：3.5-4.0x ATR，分批出場
- 最大持有：7天（normal）、5天（conservative）、10天（aggressive）
- 法人篩選：3天內任一法人買超（institutional_filter）

---

### 📈 分類 B：DCA（長期定投）

**職責**：定期定額累積低成本部位，養股不炒短

**核心腳本：**
| 腳本 | 功能 |
|------|------|
| `dca_recommendation.py` | DCA 推薦（低 RSI = 好的進場點，EXCELLENT/GOOD/FAIR/EXPENSIVE） |
| `us_etf_dca.py` | 美股 ETF DCA 分析（VTI/IWM/QQQ/SPY/BND/TLT/GLD/SLV 等） |
| `tw_value_growth.py` | 台股價值成長定投標的 |
| `us_value_growth_screener.py` | 美股價值成長定投候選 |
| `stock_strategy_updater.py` | 策略參數更新（適用於 DCA 再平衡） |
| `portfolio_tracker.py` | 部位追蹤（適用於 DCA 組合） |

**DCA 評分邏輯（dca_recommendation.py）：**
- RSI < 30 → EXCELLENT_ENTRY（+50分）
- RSI < 40 → GOOD_ENTRY（+40分）
- RSI < 50 → FAIR_ENTRY（+25分）
- RSI < 60 → NEUTRAL（+10分）
- RSI >= 60 → EXPENSIVE（+0分）
額外加分：MACD黃金交叉、MA多頭排列、機構買超

---

### 🎯 分類 C：ETF（指數被動投資）

**職責**：ETF 篩選與進場時機判斷，含槓桿/反向 ETF

**核心腳本：**
| 腳本 | 功能 |
|------|------|
| `etf_analysis.py` | 台股+美股 ETF 完整分析（16:30收盤後自動） |
| `etf_best_return.py` | ETF 報酬排名 |
| `tw_active_etf_tracker.py` | 台股主動型 ETF 追蹤 |
| `us_active_etf_screener.py` | 美股主動型 ETF 篩選 |
| `leverage_etf_analysis.py` | 槓桿/反向 ETF 分析（SOXL/TQQQ/QLD 等） |
| `leverage_etf_db.py` | 槓桿 ETF 資料庫建置 |
| `tw_etf_analysis.py` | 台股 ETF 分析 |

**ETF 評分權重（etf_analysis.py）：**
- RSI 35-50（進場區間）：30分
- MACD > 0：20分
- MA20 > MA60（多頭）：15分
- 6M 報酬 > 15%：25分
- 殖利率 > 3%：10分
- 買進門檻：60分，觀望門檻：40分

---

## 二、決策委員會 — 慢思考 SOP

### 2.1 決策委員會成員

| 成員 | 角色 | 負責領域 |
|------|------|---------|
| **Tina-Macro** | 宏觀數據整合 | 地緣政治、總經數據、市場情緒 |
| **Nana** | 短線波段交易 | 波段進場/出场、個股層級執行 |
| **Leo** | 中期趨勢追蹤 | 動能策略、趨勢確認 |
| **Ray** | ETF/被動投資 | ETF篩選、DCA、長期持有 |
| **Maggy** | 美股長線 | 美股成長股、基本面分析 |

### 2.2 慢思考觸發條件

以下情境必須啟動「慢思考」模式，不走快速決策路徑：

1. **新策略開發**：新增任何策略腳本之前
2. **回測結果解讀**：重大績效數據出來後（勝率變化>10%，PnL大幅下滑）
3. **市場體制轉換**：TWII RSI 突破 75 或跌破 30（從 OVERBOUGHT/OVERSOLD 恢復）
4. **黑名單更新**：任何股票加入/移除黑名單
5. **每月策略複審**：每月第一個交易日
6. **重大亏损案件**：單筆亏损 >5% 或單日组合亏损 >3%

### 2.3 慢思考流程（5步）

```
步驟 1 → 數據收集（Data Collection）
        Tina-Macro：整合 macro_data_fetcher（地緣/總經/市場數據）
        耗時：即時

步驟 2 → 現況診斷（Situation Diagnosis）
        全委員會：對照 unified_strategy_config.json 現有參數
        確認市場 regime（OVERBOUGHT/NEUTRAL/OVERSOLD）
        耗時：5-10分鐘

步驟 3 → 方案評估（Option Evaluation）
        列出所有可行策略（波段/DCA/ETF 三選項）
        評估每個方案的風險/報酬/持有期/最大亏损
        耗時：10-20分鐘

步驟 4 → 共識形成（Consensus）
        委員會表決（至少3/5成員同意）
        異議記錄在案
        耗時：5分鐘

步驟 5 → 付諸執行（Execution）
        分配給對應 Agent（Nana/Leo/Ray/Maggy）
        寫入 decision_log（tina_autonomous.db）
        設定追蹤與回測時程
```

### 2.4 快速決策路徑（自動執行）

適用於：日常掃描、標準進場訊號、常規報告

```
Tina-Macro（ Macro 日報）
  ↓
Nana（ 波段掃描 → 進場執行）
  ↓
Ray（ ETF/DCA 建議 → 定期定額）
```

---

## 三、新增：台美股長期持有成長股策略

### 3.1 策略定位

**目標**：提供一個適合長期持有（6-24個月）的成長股策略，補足波段（<10天）和 DCA（月頻）之間的中間地帶。

**與現有策略的差異：**
| 屬性 | 波段（Swing） | 長期持有（Growth） | DCA |
|------|-------------|------------------|-----|
| 持有期 | 5-10天 | 6-24個月 | 長期不停損 |
| RSI 進場 | < 55 | < 50 | < 40 最好 |
| 停損 | -8% 或 2x ATR | -20% | 不停損 |
| 停利 | +10-15% | +50-100% | 不停利 |
| 評估頻率 | 每日 | 每月 | 每季 |
| 基本面要求 | 低 | 高（營收成長>15%） | 低 |

### 3.2 候選清單（初始池）

**台股（TW）：**
- 半導體設備：的家、科嶸、容易
- AI 供應鏈：創意、世芯-KY、智原
- 工業自動化：台達電、鴻海、广達
- 綠能：雲豹、泓德、寶佳

**美股（US）：**
- AI 半導體：AMD、NVIDIA、博通
- 雲端/AI：微軟、Meta、Google
- 生產力工具：Salesforce、ServiceNow、Workday
- 基礎建設：Arista、Palantir、Lanium

### 3.3 進場標準（Growth-Long Entry）

```
必要條件（全部滿足）：
1. RSI(14) < 50
2. MA20 > MA60（多頭排列）
3. 營收 YoY > 15%
4. 近3月無重大負面新聞
5. 法人連續買超（3天內）

加分條件：
+ EPS 上修 > 10%
+ 目標價上調
+ 新產品/新客戶公告
+ 產業景氣向上的確認
```

### 3.4 出場標準（Growth-Long Exit）

```
主要出场：
- 持有期達到 18 個月（無論績效）
- RSI(14) > 75（嚴重超買）
- 追蹤止損：從高點拉回 20%

次要出场：
- 基本面惡化（營收連續2季下滑）
- 產業景氣轉向
- 發現更好的替代標的
```

---

## 四、模擬交易引擎規格

### 4.1 架構

```
tina_paper_trading.py（已存在，需升級）
    ↓
新增：growth_paper_engine.py（長期持有專用）
    ↓
backtest_framework.py（通用回測框架）
    ↓
decision_committee_vote.py（委員會表決）
```

### 4.2 回測框架（backtest_framework.py）

```python
# 核心回測引擎
class BacktestEngine:
    - run_backtest(strategy, start_date, end_date)
    - calculate_metrics(): 勝率、Sharpe、Max Drawdown
    - generate_report(): HTML報告輸出
    - compare_strategies(): 波段 vs Growth vs DCA

# 策略池
    - swing_strategy: 波段策略（from tina_backtest_engine.py）
    - growth_strategy: 長期成長策略（new）
    - dca_strategy: 定投策略（from us_etf_dca.py）
    - etf_strategy: ETF策略（from etf_analysis.py）
```

### 4.3 關鍵績效指標

| 指標 | 波段 | 長期持有 | DCA |
|------|------|---------|-----|
| 持有期 | 5-10天 | 6-24月 | 長期 |
| 目標報酬 | +10-15% | +50-100% | 不設定 |
| 容忍亏损 | -8% | -20% | -30% |
| Sharpe 目標 | >1.5 | >1.0 | >0.8 |
| Max Drawdown | <15% | <30% | <40% |

---

## 五、開發時程

| 階段 | 任務 | 負責 | 預計完成 |
|------|------|------|---------|
| 1a | 建立三大分類腳本地圖 | Tina | 2026-05-09 |
| 1b | 寫入 configs/strategy_map.json | Tina | 2026-05-09 |
| 2a | 決策委員會 SOP 文件 | Tina | 2026-05-10 |
| 2b | 升級 tina_autonomous_decision.py（慢思考流程） | Tina | 2026-05-11 |
| 3a | 開發 growth_paper_engine.py | Tina | 2026-05-12 |
| 3b | 建立 growth_candidates.json 候選清單 | Tina | 2026-05-12 |
| 4a | backtest_framework.py（通用框架） | Tina | 2026-05-13 |
| 4b | 歷史數據回測（2023-2026） | Tina | 2026-05-14 |
| 5a | decision_committee_vote.py | Tina | 2026-05-15 |
| 5b | 模擬交易啟動 + 委員會整合 | Tina | 2026-05-16 |

---

## 六、依賴關係

```
Phase 1 完成後才能做 Phase 2（腳本地圖不完整就無法重整SOP）
Phase 2 完成後才能做 Phase 3（沒有SOP就無法開心策略開發）
Phase 3 + 4 完成後才能做 Phase 5（策略和回測沒驗證就無法模擬交易）
```

---

**下一步：Phase 1a 啟動 — 盤點並建立三大分類腳本地圖，寫入 `configs/strategy_map.json`**