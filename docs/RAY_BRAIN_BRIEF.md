# Ray Brain 大腦邏輯簡報

## 系統定位

```
你是 Ray，不是 Tina。
Jo 的專屬美股 ETF Agent + Qwen 本地大腦協調者。
專注：VTI/VOO/QQQ/BND/VEA DCA / 美股波段操作
風格：執行導向，簡潔直接，不廢話。
```

---

## 三層分工架構

```
┌─────────────────────────────────────────────────────┐
│  Layer 0 — 硬體層（i9-13900H / RTX 4050 / 32GB）   │
│                                                     │
│  GPU: Ollama 推理（ray-v1 / ray-deep-v1）           │
│  CPU: i9 E-cores → 背景回測 | P-cores → 即時處理   │
│  RAM: 34GB 可用，13GB 當前空閒                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Layer 1 — 本地 Python（不需要 LLM，< 0.5s）       │
│                                                     │
│  ray_brain.py::local_indicators()                   │
│  ray_engine.py::run_backtest()                      │
│  • EMA / RSI / KDJ / MACD 計算                      │
│  • 30日滾動 Sharpe / MDD / WinRate                 │
│  • Math Gate：Sharpe≥1.5 + MDD≤15% + Win≥45%       │
│  • 100% 本地運行，不走網路                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Layer 2 — Qwen 1.5B（ray-v1，2-3s 回應）           │
│                                                     │
│  用途：80% 日常任務                                  │
│  • 訊號評分（score 0-5 → BUY/WATCH/NEUT）           │
│  • 策略 JSON 快速提案                               │
│  • 失敗 wisdom 初審分類                             │
│  • NL2CodeValidator 二次驗證                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Layer 3 — Qwen 7B（ray-deep-v1，25-35s 回應）      │
│                                                     │
│  用途：20% 複雜任務（confidence < 0.5 才觸發）       │
│  • 深度歸因分析（失敗 wisdom 診斷）                  │
│  • 策略進化與重建                                   │
│  • 蒸餾 teacher（黃金案例 → 微調資料）              │
│  • Connors RSI / 德哈普雷拉 策略對齊                │
└─────────────────────────────────────────────────────┘
```

---

## 決策流程

```
收到訊號（NVDA / QQQ / VTI）
        │
        ▼
┌───────────────────┐
│ Layer 1 本地計算   │ ← 完全離線，< 0.5s
│ EMA20 / RSI / KDJ │
│ MACD / Momentum   │
└───────┬───────────┘
        │ 指標字典
        ▼
┌───────────────────┐
│ Math Gate 把關     │  Sharpe < 1.5 ❌ → 刷掉（NEUT）
│ Sharpe≥1.5        │  Sharpe ≥ 1.5 ✅ → 下一關
│ MDD ≤ 15%          │
│ WinRate ≥ 45%      │
└───────┬───────────┘
        │ passed=True
        ▼
┌───────────────────┐
│ Layer 2: 1.5B 提案 │ ← 2-3s，生成策略 JSON
│ NL2Code 驗證       │
└───────┬───────────┘
        │ 策略 JSON + confidence
        ▼
    ┌───────────┐
    │ confidence │
    │    < 0.5   │ → YES → Layer 3: 7B 深度分析（25-35s）
    └─────┬─────┘
          │ NO
          ▼
┌───────────────────┐
│ 寫入 signals_log   │  評分 → BUY/WATCH/NEUT
│ 寫入 wisdom_logs   │
└───────────────────┘
```

---

## 資料持久化（ray_wisdom.db）

```
SQLite WAL 模式，並發安全，12 張表格

核心表格：
├── wisdom_logs        360筆  所有策略輸入/輸出
├── wisdom_corrections 144筆  7B 深度修正記錄
├── backtest_reports   206筆  回測結果（Sharpe>0.8: 18筆）
├── signals_log          6筆  已認證交易訊號
├── positions_log        0筆  實際持倉（待串接）
└── daily_performance    0筆  每日績效（待建立）
```

---

## LLM 使用比例（優化後）

```
1.5B（ray-v1）   ████████████████████████████  80%
7B（ray-deep-v1）████                              20%

理由：
• 1.5B 快取後 2.5s，7B 快取後 27s
• 1.5B 足以處理 80% 日常評分/分類任務
• 7B 只做：深度歸因、策略進化、蒸餾 teacher
```

---

## 自動化排程（Windows Task Scheduler）

```
Ray Tina Daily   平日 08:30  盤前掃描 + us_momentum
Ray Tina Evening 平日 17:00  蒸餾 + 權重更新
Ray Tina Weekly  週五 22:00  Unsloth 微調（待修復）
```

---

## 蒸餾 Pipeline（受阻）

```
Step 1: 黃金案例挖掘（Sharpe>0.8）     [DONE]  18筆
Step 2: 7B 深度修正                   [DONE]  144筆
Step 3: 生成 JSONL 蒸餾資料集          [待執行]
Step 4: Transformers PEFT 微調         [待執行] ← 繞過 Unsloth/triton
Step 5: 部署新權重到 Ollama             [待執行]
```

---

## 核心腳本地圖

```
ray_brain.py          — 大腦協調层（Layer 1-3 路由）
ray_engine.py         — 回測引擎 + 技術指標
ray_data_center.py    — SQLite CRUD + WAL 持久化
ray_nl2code.py        — JSON Schema 驗證 + 自動修正
ray_evolution.py      — 自主學習循環（learn/self_correct/update_weights）
ray_self_correct.py   — 雙層 LLM 自我修正（1.5B初審 + 7B複審）
ray_gold_miner.py     — 黃金案例挖掘（Sharpe > 1.5）
ray_train_tina.py     — 蒸餾訓練（待 Transformers PEFT）
us_momentum.py        — 技術動能掃描（1D/5D/20D）
us_scan_live.py       — 即時技術掃描（MA20/MA60/RSI/MACD/KDJ）
tina_health_check.py  — 系統健康檢查
tina_daily_self_correct.py — 每日盤後自動修正循環
```

---

## 健康分數

```
8/10 🟢 健康

已解決：PyTorch CUDA 安裝 ✅ | backtest_reports 填滿 ✅
       wisdom_corrections 批次處理 ✅ | Windows Task Scheduler ✅

待解決：Unsloth triton 版本衝突 → 用 Transformers PEFT 替代
        daily_performance = 0 → 待建立
        weight > 2.0 = 0 → 沒有高權重策略
```

---

## 決策原則

1. **執行優先**：討論確定了就執行，不拖延
2. **風險第一**：任何交易先確認停損
3. **透明誠實**：失敗了立刻承認，不找藉口
4. **1.5B 先，7B 後**：80% 任務由 1.5B 處理
5. **本地 Python 優先**：指標計算不走 LLM