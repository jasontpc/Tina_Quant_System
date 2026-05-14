# Ray LLM Router Config
# LLM 路由分層原則（v2 - 2026-05-12 更新）

mode: auto

# ══════════════════════════════════════════════════════════════
# LLM 路由分層（Layer 0-3）
# ══════════════════════════════════════════════════════════════
# Layer 0: 純本地計算 → 不走 LLM
#   us_momentum.py, us_scan_live.py, ray_engine.py
#   技術指標、Sharpe/MDD 計算、SQLite 持久化
#
# Layer 1: 快速策略（< 3 秒）→ ray-v1（本地 Ollama）
#   daily_scan, quick_signal, position_check, signal_parse
#
# Layer 2: 深度推理（3-15 秒）→ MiniMax Remnant（雲端）
#   backtest_summary, deep_analysis, attribution, macro_outlook, json_validate
#
# Layer 3: 連網學習 → MiniMax（帶 web fetch）
#   web_learn, news_summary, sentiment, macro_news, earnings_summary
#
# 數據獲取（永遠不走 LLM）：yfinance, finmind, twstock
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# 本地模型映射（Ollama）
# ══════════════════════════════════════════════════════════════
ollama:
  base_url: "http://localhost:11434/api/chat"

  # Layer 1: 快速任務（< 3s）
  layer1_primary: "ray-v1"           # Qwen 1.5B (986MB) - 主力
  layer1_alt1:   "qwen2.5:3b"      # Qwen 2.5 3B (1.9GB) - ray-v1 失敗時備用
  layer1_alt2:   "qwen3.5:4b"      # Qwen 3.5 4B (3.4GB) - 緊急備用

  # Layer 2: 深度任務
  layer2_primary: "ray-deep-v1"    # Qwen 7B (4.7GB) - Ollama 主力深度
  layer2_alt1:    "qwen2.5:7b"     # Qwen 2.5 7B (4.7GB) - MiniMax 失敗時備用

# ══════════════════════════════════════════════════════════════
# MiniMax 模型
# ══════════════════════════════════════════════════════════════
minimax:
  model: "minimax/MiniMax-M2.7"  # Remnant
  layer2_tasks: "deep_analysis, backtest_summary, attribution, macro_outlook, json_validate"
  layer3_tasks: "web_learn, news_summary, sentiment, macro_news, earnings_summary"

# ══════════════════════════════════════════════════════════════
# 腳本 × Router 整合狀態（2026-05-12）
# ══════════════════════════════════════════════════════════════
# ✅ 已整合（走 Router）：
#   ray_brain.py, ray_integrated_brain.py, ray_web_learner.py,
#   ray_econ_learner.py, ray_self_correct.py, tina_daily_self_correct.py,
#   ray_cloud_brain.py, news_sentiment.py
#
# ✅ 無需 LLM（純本地計算）：
#   us_momentum.py, us_scan_live.py, ray_engine.py,
#   llm_daily_report.py, llm_status.py, macro_report.py

token_save:
  batch_size: 10
  max_input_tokens: 3000
  max_output_tokens: 1000

fallback:
  action: "chain_fallback"
  # Layer 1: ray-v1 → qwen2.5:3b → qwen3.5:4b → error
  # Layer 2: MiniMax → ray-deep-v1 → qwen2.5:7b → error
  error_note: "Router 降級：MiniMax → Ollama 備用鏈 → error"