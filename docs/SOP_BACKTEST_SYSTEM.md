# Tina Quant System — 全系統回測數據標準作業程序 (SOP)

**版本：** v3.14 | **日期：** 2026-05-14 | **維護：** Tina

---

## 📊 全系統回測數據總覽

| 系統 | 類型 | 交易筆數 | 勝率 | 平均報酬 | 狀態 |
|:----:|:----:|--------:|:----:|---------:|:----:|
| **Tina V3 Alpha** | 美股/ETF 波段 | **260** | **63.1%** ✅ | **+2.17%** | ✅ 主力 |
| **Nana 波段** | 台股百大 | **605** | **58.2%** ✅ | **+1.60%** | ✅ 主力 |
| **Leo 台股波段** | 台股AI科技 | **290** | **47.2%** ⚠️ | **-0.11%** | ⚠️ 落後 |
| **Maggy 美股** | 美股動量 | 0 ❌ | — | — | ❌ 無數據 |
| **Ray ETF** | TW/US ETF | 0 ❌ | — | — | ❌ 無數據 |

**有效總交易：1,155 筆 | 加權勝率：56.5%**

---

## 🎯 各系統策略參數

### Tina V3 Alpha（美股/ETF 波段）

| 參數 | 數值 |
|:-----|:-----:|
| 進場 RSI | < 65（理想 35-50）|
| 停利 ATR | 2x |
| 停損 ATR | 3x |
| 最大持有 | 10 天 |
| 評分門檻 | Entry Score ≥ 350 |

**Universe：** 154 支美股（us_history.db）
**關鍵發現：** RSI 35-40 = 100% 勝率（真正最佳區間）

---

### Nana 波段（台股百大）

| 參數 | 數值 |
|:-----|:-----:|
| RSI 進場 | 40-65 |
| MA 條件 | MA20 > MA60（多頭）|
| ATR 最小 | ≥ 0.3% |
| 法人分門檻 | InstTotal ≥ 10 |
| 持有天數 | 一般 ≤ 30 天 |
| 停利 | TP/SL 組合 |

**Universe：** 台股百大（60檔）
**關鍵發現：** 持有 >30天 + RSI>50 = 最危險組合

---

### Leo 台股波段（AI科技股）

| 參數 | 數值 |
|:-----|:-----:|
| RSI Period | 12 |
| RSI Threshold | 40 |
| Hold Days | 10 |
| Take Profit | 10% |
| Stop Loss | 8% |
| Trailing ATR | 1.5x |
| ADX Threshold | 15 |

**三位一體進場哲學：**
- 均線（MA）= 路徑確認（MA20 > MA60）
- MACD = 引擎推力（MACD Hist > 0）
- KDJ = 油門精準打擊（K 低檔交叉）

**最優 Walk-Forward：** val_wr 72.7%，score 80.32

---

## ⏰ 全系統排程

### 每日自動化（每個交易日）

| 時間 | Job | 功能 | Timeout |
|:-----|:-----|:-----|--------:|
| **07:50** | 7B Warmup | 預熱 ray-deep-v1 | 300s |
| **08:30** | 開盤前預載 | @ray_singleton_high_priority VRAM 預載 | 120s |
| **09:00** | Nana 百大掃描 | 分析台股百大，產出 Top10 信號 | 320s |
| **09:00** | Leo 台股波段 | 分析8檔AI科技股+持倉監控 | 320s |
| **09:10** | 模擬倉開盤掃描 | 持倉開盤前檢查 | 420s |
| **09:00** | Tina 風控檢查 | RSI/持有天數/停損條件 | 320s |
| **10:00** | Tina 自主決策 | 五大層分析（目標/風控/持倉/市場/行動）| 180s |
| **11:00** | Tina Cron Governor | 每小時系統監控 | 90s |
| **14:00** | Ray 歷史歸納蒸餾 | 第一階段智力灌頂 | 320s |
| **14:00** | Ray 全語意蒸餾 | 語意標籤規則蒸餾 | 320s |
| **14:05** | Ray 失敗歸因蒸餾 | Phase1 7B → 10大禁止規則 | 320s |
| **14:05** | Ray 邏輯固化重生 | 失敗歸因蒸餾（每日）| 450s |
| **21:00** | Tina 風控檢查 | 收盤後風控複查 | 320s |

### 每週自動化

| 時間 | Job | 功能 | Timeout |
|:-----|:-----|:-----|--------:|
| **週六 10:00** | Leo 每週回測更新 | 更新 leo_backtest_report_v2.json | 150s |
| **週六 10:00** | Tina 每週蒸餾 | Pattern/Lesson 晉升審查 | 300s |
| **週六 11:00** | Tina V3 Alpha 回測 | 自動回測並更新 stores/backtest_report.json | 300s |

### 每月自動化

| 時間 | Job | 功能 | Timeout |
|:-----|:-----|:-----|--------:|
| **每月1日 11:00** | Leo 矩陣優化 | Walk-Forward 重掃描 | 600s |
| **每月1日 12:00** | Nana 參數更新 | 波段參數複檢 | 300s |

---

## 📈 回測數據更新 SOP

### 每日（自動）
```
stores/portfolio/trades.log 持續寫入
→ 每週六 10:00 由 leo_backtest_report_generator.py 彙整
→ 每季手動驗證一次
```

### 每週六（Leo 回測更新）
```bash
python C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\leo_backtest_report_generator.py
# 讀取 teams/leo/reports/sim_trades.json（290筆模擬交易）
# 產出 teams/leo/reports/leo_backtest_report_v2.json
```

### 每季（Nana 波段回測更新）
```bash
cd C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana
python nana_scanner.py --backtest
# 讀取 data/tina_master.db（MarketData）
# 產出 teams/nana/reports/nana_backtest_report.json
```

---

## 🔍 數據質量標準

### 合格標準

| 指標 | 合格線 | 警告線 |
|:-----|:------:|:------:|
| 勝率（Win Rate）| ≥ 50% | < 45% |
| 平均報酬（Avg Return）| > 0% | ≤ 0% |
| 交易筆數（Min Trades）| ≥ 30 筆 | < 20 筆 |
| 最大虧損（Max Drawdown）| < 20% | ≥ 20% |
| 夏普比率（Sharpe）| > 1.0 | ≤ 0.5 |

### 數據品質狀態

| 系統 | 狀態 | 說明 |
|:-----|:-----|:-----|
| Tina V3 Alpha | ✅ 優秀 | 63.1% 勝率，+2.17% 均報酬 |
| Nana 波段 | ✅ 良好 | 58.2% 勝率，+1.60% 均報酬 |
| Leo 台股波段 | ⚠️ 待優化 | 47.2% 勝率，目標提升至 55%+ |
| Maggy 美股 | ❌ 無數據 | 需重新執行回測 |
| Ray ETF | ❌ 無數據 | 需確認 ray/backtest_report.json 格式 |

---

## 🛡️ 風控規則（通用）

| 規則 | 限制 |
|:-----|:-----:|
| 單筆最大虧損 | -8% |
| 總部位上限 | 40% |
| RSI 進場上限 | < 65 |
| 高Beta停損 | ATR 1.5x |
| 持有>30天 + RSI>50 | 警戒，考慮减倉 |
| TWII RSI > 85 | 全市場過熱，觀望 |

---

## 📋 SOP 執行檢查清單

### 每日開盤前（08:30-09:00）
- [ ] 08:30 VRAM 預載完成
- [ ] 09:00 Nana + Leo 分析出爐
- [ ] 讀取 positions.json 確認持倉狀態
- [ ] TWII RSI > 80 → 全系統觀望

### 每週六維護日
- [ ] Leo 回測報告更新（10:00）
- [ ] Tina 每週蒸餾（10:00）
- [ ] Tina V3 Alpha 回測更新（11:00）
- [ ] 審查無效系統（Maggy/Ray）

### 每季策略複檢
- [ ] 各系統勝率是否維持 > 50%
- [ ] 平均報酬是否維持 > 0
- [ ] 是否有新系統需要納入

---

_Last updated: 2026-05-14 by Tina_
_下次檢查：2026-06-14_