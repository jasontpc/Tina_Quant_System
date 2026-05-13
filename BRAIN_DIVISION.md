# Ray 大腦分工藍圖（蒸餾管道版）
# 本地脚本 vs Qwen 各自的職責邊界

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
層級一：本地 Python（不需要 LLM）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
負責：客觀計算、數據抓取、數學把關

│ 腳本               │ 職責                              │
│--------------------│-----------------------------------|
│ us_momentum.py     │ 1D/5D/20D 動能 + KDJ 計算         │
│ us_scan_live.py    │ MA20/MA60 + RSI + MACD Hist + KDJ │
│ ray_data_center.py │ SQLite 持久化（所有數據）           │
│ ray_engine.py      │ 回測引擎（Sharpe>1.5 / MDD<15%）   │
│ ray_nl2code.py     │ JSON Schema 驗證（拦截幻覺）        │
│ ray_gold_miner.py  │ 黃金樣本篩選器（蒸餾第一步）        │
│ ray_logic_aligner.py│ Logic Alignment 蒸餾器（第二步）  │
│ ray_train_tina.py  │ Unsloth 微調 1.5B（第三步）        │

摩擦成本：0.15% 美股 / 0.54% 台股
Math Gate：Sharpe>1.5 + MDD<15% + WinRate>45%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
層級二：Qwen 1.5B（ray-v1）— 蒸餾學生
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
職責：即時策略提案、高頻篩選、簡單 JSON 格式化
現狀：
  → 未蒸餾：基礎 qwen2.5:1.5b
  → 蒸餾後：ray-tina-v1（LoRA 權重）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
層級三：Qwen 7B（ray-deep-v1）— 蒸餾老師
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
職責：複雜推理、歸因分析、策略進化（下載中）
用途：
  → 當導師，對 1.5B 輸出打分與修正
  → Logic Alignment 的核心

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Distillation Pipeline（蒸餾管線）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Gold Miner
  wisdom_logs + backtest_reports
  → Sharpe>1.8 + MDD<12% + Win>45% + Trades>20
  → ray_gold_train.jsonl (instruct)
  → ray_causal_train.jsonl (causal SFT)

Step 2: Logic Aligner
  1.5B 推理 → 7B 批改 → 修正對
  → ray_logic_alignment.jsonl

Step 3: Unsloth Fine-Tune
  ray_causal_train.jsonl + ray_logic_alignment.jsonl
  → LoRA rank=32, 4bit, batch=2, GA=4
  → ray_tina_1.5b_lora/

Step 4: Merge & Export
  LoRA + base → GGUF
  → ollama create ray-tina-v1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
分工原則（不變）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ 本地脚本做的：
  - 數據抓取（yfinance）
  - 指標計算（RSI/KDJ/MACD/EMA）
  - 數學把關（Sharpe/MDD/WinRate）
  - 數據持久化（SQLite）
  - JSON Schema 驗證

✗ Qwen 做的：
  - 自然語言 → 結構化策略（NL2Code）
  - 市場情緒理解
  - 複雜策略優化建議
  - 歸因分析（為什麼這個策略有效）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
實際工作流
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. us_momentum.py → 抓到股票數據 → 計算指標
2. ray_engine.py → 跑 Sharpe/MDD 把關 → 通過的信號進 SQLite
3. Qwen 1.5B → 把通過的信號轉成策略 JSON → 寫入 signals_log
4. Qwen 7B → 每日深度複習（進化學習）→ 更新 backtest_reports
5. Gold Miner → 蒸餾高Sharpe策略
6. Logic Aligner → 7B批改1.5B → 修正蒸餾
7. Unsloth → 蒸餾後的 LoRA 權重 → Ollama

_Last updated: 2026-05-12_