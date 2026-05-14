# Leo 台股波段 — 排程與標準作業程序 (SOP)

## 📊 回測有效性聲明

| 版本 | 日期 | 筆數 | 勝率 | 平均報酬 | 備註 |
|:----:|:----:|-----:|-----:|---------:|:-----|
| v1（舊）| 2026-04-26 | 24 | 33.3% ❌ | -1.3% ❌ | 刪除（樣本不足）|
| **v2（新版）** | **2026-05-14** | **290** | **47.2%** | **-0.11%** | **模擬倉真實回測** |
| **矩陣最優** | **2026-04-26** | — | **72.7% val** | — | **Walk-Forward 驗證** |

**新版結論：**
- 290 筆模擬交易（2025-01-01 ~ 2026-04-25）
- 勝率 47.2%（仍低於美股 63%）
- 2330 台積電：勝率 60.5%，平均報酬 +1.79%（最佳）
- Walk-Forward 驗證：val_wr 72.7%，score 80.32（優秀）

---

## 🎯 策略參數（最優配置）

```json
{
  "rsi_period": 12,
  "rsi_threshold": 40,
  "hold_days": 10,
  "take_profit_pct": 10,
  "stop_loss_pct": 8,
  "trailing_atr_mult": 1.5,
  "score_min": 30,
  "adx_threshold": 15
}
```

### 三位一體進場哲學

| 維度 | 角色 | 條件 |
|:-----|:-----|:-----|
| **MA 均線** | 路徑確認 | MA20 > MA60（多頭）|
| **MACD** | 引擎推力 | MACD Hist > 0 |
| **KDJ** | 油門精準打擊 | K 線低檔交叉 |

---

## ⏰ 排程設計

| Job | 時間 | 腳本 | 功能 | Timeout |
|:----|:-----|:-----|:-----|--------:|
| **Leo 每日分析** | `0 9 * * 1-5` | `leo_autonomous_cycle.py` | 8檔AI科技股分析+持倉監控 | 300s |
| **Leo 每週回測更新** | `0 10 * * 6` | `leo_backtest_report_generator.py` | 從 sim_trades.json 更新回測報告 | 120s |
| **Leo 矩陣優化（月）** | `0 11 1 * *` | `leo_matrix_optimizer.py` | Walk-Forward 參數重掃描 | 600s |

---

## 🔄 每日流程（09:00 開盤後）

```
09:00  Leo 每日分析 → 分析8檔AI科技股
         ↓
         [持倉檢查：target/stop/overheat]
         ↓
         [新進場：RSI 45-65 + pos_ma20 < 15%]
         ↓
         [產出：leo_analysis.json]
         ↓
10:00  根據需要手動干預（看 Telegram 報告）
         ↓
15:30  收盤前最終檢查
```

---

## 📈 關鍵監控指標

| 股票 | 勝利次數 | 總交易 | 勝率 | 平均報酬 | 狀態 |
|:----:|:--------:|:------:|:----:|---------:|:-----:|
| 2330 台積電 | 23 | 38 | **60.5%** | **+1.79%** | ✅ 最佳 |
| 2379 瑞昱 | 25 | 45 | 55.6% | -0.04% | ⚠️ |
| 3034 緯穎 | 24 | 51 | 47.1% | -0.58% | ⚠️ |
| 2382 廣達 | 18 | 40 | 45.0% | -0.33% | ⚠️ |
| 2317 鴻海 | 16 | 37 | 43.2% | +0.33% | ⚠️ |
| 2454 聯發科 | 15 | 38 | 39.5% | -0.91% | ❌ |
| 2376 技嘉 | 16 | 41 | 39.0% | -0.80% | ❌ |

---

## 📋 SOP 執行手冊

### 每日（09:00 開盤前）
```bash
cd C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo
python scripts/leo_autonomous_cycle.py
```
→ 讀取 `reports/leo_analysis.json` 查看訊號

### 每週六 10:00 — 回測更新
```bash
python C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\leo_backtest_report_generator.py
```
→ 更新 `reports/leo_backtest_report_v2.json`

### 每月初 — 矩陣重掃描
```bash
cd C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo
python leo_matrix_optimizer.py
```
→ 產出 `matrix_results/best_leo_params.json`

---

## 🛡️ 風控規則

| 規則 | 限制 |
|:-----|:-----:|
| 單筆最大虧損 | -8% |
| 停利目標 | +10%（或 ATR 2x trailing）|
| RSI 進場上限 | < 65 |
| RSI 進場下限 | > 30 |
| 最大持有天數 | 10 天 |
| 同時最大持倉 | 3 檔 |

---

_Last updated: 2026-05-14 by Tina_