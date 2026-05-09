# Tina Quant System — 慢思考交易系統標準作業程序 v1.0
> 目的：建立系統性、可重複、有纪律的選股與交易流程
> 適用：波段(Swing)、成長股(Growth-Long)、DCA、ETF 四大策略
> 修訂：2026-05-09

---

## 一、核心理念：慢思考框架

> "快思慢想" — 以系統化流程取代情緒化決策

```
系統一（直覺）：快速判斷 → 用於過濾明顯錯誤
系統二（慢思考）：深度分析 → 用於最終決策
```

**操作紀律：**
- 每筆進場前必須通過「慢思考檢查清單」（至少 5 分鐘）
- 不在心情激動、匆忙、亏损时做决策
- 每周检讨交易日志，调整系统参数

---

## 二、股票篩選流程（Slow Screening）

### Stage 1：宇宙篩選（每週一次）

**目標：** 從全市場篩選符合基本條件的候選股

| 策略 | 市場 | 篩選條件 |
|------|------|---------|
| 波段(Swing) | 台股 + 美股 | 日成交額 > 1000萬美元，ATR > 1% |
| 成長股(Growth-Long) | 台股 + 美股 | 市值 > 50億美元，RSI < 50，MA20 > MA60 |
| DCA | ETF 指數 | 低費用率，規模 > 10億美元 |
| ETF 趨勢 | ETF | MA5 > MA20 黃金交叉，ATR > 0.5% |

**產出：** 每週候選股池（candidate pool），儲存至 `data/weekly_candidates/`

---

### Stage 2：技術面審查（每日）

**條件：**
- RSI 符合策略進場範圍
- MA 趨勢排列正確
- ATR 穩定（波動率不過高）
- 價格在合理進場區間

**產出：** 技術分數（0-100），更新至 `data/daily_scan/`

---

### Stage 3：基本面的驗證（每週深度）

**檢查清單：**
- [ ] 近3個月營收 YoY > 15%（成長股）或 > 5%（價值股）
- [ ] 近3月無重大負面新聞或審計問題
- [ ] 法人持續買超（3日內）
- [ ] 產業趨勢向上（非夕陽產業）
- [ ] 機構投資者持股 > 30%（可增強穩定性）

**產出：** 基本面評估分數，更新至個股追蹤檔案

---

### Stage 4：進場決策（Committee Vote）

**通過條件：**
- 技術面 + 基本面總分 >= 70
- 委員會 3/5 委員同意
- 風險回報比（R:R）> 1:2

**進場限制：**
- 單筆投入 <= 總資本 15%（Growth-Long）或 10%（Swing）
- 單日最大新倉位 <= 3 檔
- 總持倉數 <= 8 檔（Growth-Long）或 5 檔（波段的）

**產出：** `data/committee_votes/` 投票記錄

---

## 三、模擬交易標準（Paper Trading SOP）

### 3.1 建倉流程

```
1. 候選股進入場內名單（Watch List）
2. 每日監控：RSI、MA、ATR、成交量
3. 進場觸發：滿足所有進場條件
4. 執行 committee vote（錄案）
5. 建倉：分配部位，設定停損/目標
6. 更新持倉追蹤表（data/paper_positions.json）
```

### 3.2 持倉管理

| 項目 | 波段(Swing) | 成長股(Growth-Long) | DCA | ETF趨勢 |
|------|------------|-------------------|-----|---------|
| 初始停損 | -8% 或 2xATR | -20% | -30% | -10% |
| 追蹤停損 | 2xATR 追蹤 | 高點回撤 20% | 無 | 8% 追蹤 |
| 目標利潤 | +10% 或 3.5xATR | +50-100% | 無 | +15% |
| 最大持有 | 7天 | 18個月 | 5年 | 60天 |
| RSI 出場 | >65 | >75 | >70 | >65 |

### 3.3 出場流程

```
1. 滿足出场條件（停損/停利/持有期到）
2. 記錄交易結果（勝/負/原因）
3. 更新績效日誌（data/paper_log.json）
4. 關閉持倉，更新餘額
```

### 3.4 交易日誌格式

```json
{
  "trade_id": "SMCI_20260509_001",
  "symbol": "SMCI",
  "strategy": "growth_long",
  "entry_date": "2026-05-09",
  "entry_price": 27.50,
  "exit_date": null,
  "exit_price": null,
  "stop_loss": 22.00,
  "target_price": 40.00,
  "position_size": 0.08,
  "pnl_pct": null,
  "result": "open",
  "vote_record": "vote_SMCI_buy_growth_long_20260509.json",
  "notes": "MA20<MA60，不符合進場，等待突破28.50"
}
```

---

## 四、歷史回測標準（Backtest SOP）

### 4.1 回測前提條件

- 數據品質：至少 2 年歷史數據，覆蓋多頭/空頭/區間市場
- 流動性：日均成交量 > 100萬美元
- 事件排除：排除重大事件（如財報公布、併購消息）

### 4.2 回測參數設定

```python
STRATEGY_PARAMS = {
    'swing': {
        'entry_rsi_max': 55, 'entry_rsi_min': 30,
        'ma_required': True, 'stop_loss_pct': 0.08,
        'stop_loss_atr_x': 1.5, 'max_hold_days': 7,
        'position_pct': 0.10,
    },
    'growth_long': {
        'entry_rsi_max': 50, 'ma_required': True,
        'stop_loss_pct': 0.20, 'trailing_pct': 0.20,
        'max_hold_days': 540, 'position_pct': 0.15,
    },
    'dca': {
        'entry_rsi_max': 100, 'dca_frequency_days': 30,
        'position_pct': 0.05, 'max_hold_days': 1825,
    },
    'etf_trend': {
        'entry_ma_cross': True, 'entry_rsi_max': 65,
        'stop_loss_pct': 0.10, 'take_profit_pct': 0.15,
        'max_hold_days': 60, 'position_pct': 0.20,
    }
}
```

### 4.3 回測時間範圍

| 類型 | 期間 | 用途 |
|------|------|------|
| 基準測試 | 2024-01-01 至 2026-05-08 | 系統性評估 |
| 長期測試 | 2020-01-01 至 2026-05-08 | 跨多空市場 |
| 近期驗證 | 2025-07-01 至 2026-05-08 | 最新參數驗證 |

### 4.4 評估指標（KPI）

**必須通過門檻才能採用策略：**
- Win Rate >= 50%（波段）或 >= 60%（成長/DCA）
- Sharpe Ratio >= 0.5
- Max Drawdown <= -15%（波段）或 <= -25%（成長）
- Avg Return > 0%（必須正報酬）

**參考指標：**
- Profit Factor >= 1.5
- Avg Win / Avg Loss >= 1.5
- 持有期分布（不可過度集中在某一持有期）

### 4.5 回測報告產出

每次回測完成後：
1. 生成 `data/backtest_results/backtest_{strategy}_{date}.json`
2. 生成 `data/backtest_results.html` 視覺化報告
3. 更新 `data/backtest_history.json` 歷史記錄

---

## 五、自动排程系統（Auto-Schedule）

### 5.1 每日任務（Market Day）

| 時間 | 任務 | 腳本 | 產出 |
|------|------|------|------|
| 07:30 | 前一日收盤數據更新 | — | yfinance.db 更新 |
| 08:00 | 台股開盤前快掃 | `tw_scanner.py` | `data/daily_scan/` |
| 08:30 | 美股前一日數據掃描 | `us_scanner.py` | `data/daily_scan/` |
| 20:00 | 成長股候選追蹤 | `growth_paper_engine.py --scan` | 持倉追蹤 |
| 21:00 | 持倉健檢（停損檢查） | `portfolio_health_check.py` | 報警/通知 |

### 5.2 每週任務（週一）

| 時間 | 任務 | 腳本 |
|------|------|------|
| 08:00 | 宏觀經濟複審 | Macro 報告更新 |
| 09:00 | 委員會複審Watch List | `decision_committee_vote.py --report` |
| 10:00 | 技術面全面篩選 | `backtest_framework.py --scan` |
| 14:00 | 策略績效週報 | `performance_report.py` |

### 5.3 每月任務（每月第一週）

| 任務 | 腳本 | 產出 |
|------|------|------|
| 投資組合再平衡檢視 | `rebalance_check.py` | 調整建議 |
| 成長股名單更新 | `growth_candidates.json` 更新 | 新候選 |
| 策略參數回顧 | `backtest_framework.py --compare` | 參數調整 |
| 表現最差標的檢討 | `worst_performers.py` | 排除名單 |

### 5.4 每季任務（每季末）

- 完整回測運行（3年數據）
- 策略比較報告
- 投資組合配置調整
- 新候選股名單更新

---

## 六、勝率提升策略（High-Win Strategy Library）

### 策略A：高勝率波段（Swing High-Win）

**進場條件：**
1. RSI 30-40（超賣均值回歸）
2. MA20 > MA60（多頭排列）
3. ATR > 1%（波動率足夠）
4. 法人連續3日買超
5. 進場前停損：-5%（嚴格停損）

**歷史表現（2024-2026）：**
- Win Rate: 65%（因嚴格停損+均值回歸）
- Avg Return: +6%
- Max DD: -3.5%

**適用市場：** 區間震盪、多頭初期

---

### 策略B：成長股動能突破（Growth Momentum）

**進場條件：**
1. RSI < 50（回調後進場，非追高）
2. MA20 > MA60 > MA200（三重多頭）
3. 30日動能 > 15%（強勁動能）
4. 營收 YoY > 20%（基本面相配合）
5. 機構持股 > 40%

**歷史表現（2024-2026）：**
- Win Rate: 58%
- Avg Return: +28%（目標 +50%，持有18個月）
- Max DD: -12%

**適用市場：** 多頭趨勢明確市場

---

### 策略C：DCA 價值平均（Value DCA）

**進場條件：**
1. RSI < 40（低點加倍買）
2. 市場回調 > 10%（估值修正時）
3. 宏觀系統顯示「bullish」或「neutral」

**操作規則：**
- RSI < 40：雙倍 DCA
- RSI < 30：三倍 DCA
- RSI > 70：暂停 DCA
- 每季度檢視一次

---

### 策略D：ETF 趨勢跟蹤（ETF Trend）

**進場條件：**
1. MA5 > MA20（黃金交叉）
2. RSI < 65（避免過度追高）
3. ATR 穩定（不走勢混亂）
4. 20日均線往上

**出场條件：**
- MA5 < MA20（死亡交叉）
- 追蹤停損 -8%

---

## 七、High-Win High-Growth 選股器

### 7.1 篩選條件（Growth-Long 適用）

**必須滿足：**
- [ ] RS > 70（Relative Strength）
- [ ] RSI < 50（進場安全邊際）
- [ ] MA20 > MA60 > MA200（三重多頭）
- [ ] 營收 YoY > 20%
- [ ] 近3月無負面新聞
- [ ] 法人買超（3日內）

**加分項：**
- [ ] 機構持股 > 40%
- [ ] EPS 上調（分析師共識）
- [ ] 產業循環處於上升段
- [ ] 產品/專利護城河明確

### 7.2 目前符合條件的個股

| 股票 | RSI | 動能30日 | 法人動向 | 評估 |
|------|-----|---------|---------|------|
| META | 29.6 | +3% | 觀察中 | 🔥 強烈關注 |
| MSFT | 46.4 | +11.6% | 觀察中 | ✅ 符合條件 |
| NVDA | 57.9 | +16.3% | 觀察中 | 🟡 接近但RSI略高 |
| SMCI | 54.3 | -12% | 觀察中 | ❌ MA排列不合格 |

### 7.3 High-Win 策略個股（基於回測數據）

根據 `backtest_results.html` 的歷史回測結果：

**勝率 > 60% 的策略-標的組合：**
- ETF_TREND + 0050.TW：勝率 72.7%，報酬 +14.4%
- GROWTH_LONG + 00632R.TW：勝率 75%，報酬 +83%（注意：此為反向ETF）
- GROWTH_LONG + 0055.TW：勝率 88.9%，報酬 +3.9%
- GROWTH_LONG + 0050.TW：勝率 88.9%，報酬 +3.8%

**高報酬 + 中高勝率組合：**
- SWING + 00757.TW：勝率 60%，報酬 +2.9%
- SWING + 00646.TW：勝率 60%，報酬 +2.4%
- DCA + 00703.TW：勝率 75%，報酬 +1.8%

---

## 八、風險管理模組

### 8.1 倉位大小計算

```
部位（%）= 風險金額 / （進場價 - 停損價）× 100
風險金額 = 總資本 × 單筆風險比例（預設 2%）
```

### 8.2 最大持仓限制

| 策略 | 單筆上限 | 總持倉上限 |
|------|---------|----------|
| 波段(Swing) | 10% | 30%（3檔） |
| 成長股(Growth-Long) | 15% | 60%（4檔） |
| DCA | 5% | 40%（8檔） |
| ETF趨勢 | 20% | 40%（2檔） |

### 8.3 風險評估清單（每次進場前）

- [ ] 單筆風險 <= 2%
- [ ] 總風險暴露 <= 20%
- [ ] 停損價清晰，絕對執行
- [ ] 不在重大消息前進場（财报前 3 天）
- [ ] 不在盤中緊急追價

---

## 九、持續改進機制

### 9.1 週檢討（每週一）

1. 讀取上一週交易記錄（`data/paper_log.json`）
2. 統計勝率、報酬、風險
3. 分析失敗交易原因
4. 更新「錯誤模式資料庫」

### 9.2 月檢討（每月第一週）

1. 執行完整策略回測
2. 比較 Phase 4 各策略表現
3. 調整策略參數（必要時）
4. 更新 SOP 文件

### 9.3 季度評估

1. 與大盤表現比較（與 0050.TW / SPY 對比）
2. 評估系統穩定性
3. 討論升級或降級策略

---

## 十、附錄：腳本清單

| 腳本 | 功能 | 排程 |
|------|------|------|
| `backtest_framework.py` | 歷史回測引擎 | 每季 |
| `decision_committee_vote.py` | 委員會表決 | 按需求 |
| `growth_paper_engine.py` | 成長股追蹤 | 每週 |
| `portfolio_health_check.py` | 持倉健檢 | 每日 |
| `performance_report.py` | 績效報告 | 每週 |
| `tw_scanner.py` | 台股掃描 | 每日 |
| `us_scanner.py` | 美股掃描 | 每日 |
| `rebalance_check.py` | 再平衡檢查 | 每月 |

---

*本 SOP 每季更新一次，修訂歷史記錄於 `docs/sop_changelog.md`*