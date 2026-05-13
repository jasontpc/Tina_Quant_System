import sqlite3, os, requests

conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM wisdom_logs')
wl = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=1')
wp = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
wc = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports')
br = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM signals_log')
sl = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0.8')
g1 = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
g2 = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0')
lw = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight >= 2.0')
hw = c.fetchone()[0]

print("=== 核心邏輯與腳本索引報告 ===")
print()
print("【腳本分類索引】")
print()
print("大腦層（Layer 1-3 協調）")
print("  ray_brain.py              13 KB  — 三層分工路由（本地1/5B/7B）")
print("  ray_nl2code.py            11 KB  — JSON Schema 驗證 + 自動修正")
print()
print("回測引擎")
print("  ray_engine.py             11 KB  — 回測引擎 + 技術指標（RSI/RSI2/MACD/EMA/KDJ/Momentum）")
print("  ray_data_center.py       14 KB  — SQLite CRUD + WAL 持久化")
print()
print("自主學習")
print("  ray_evolution.py         16 KB  — 自主學習循環（learn/self_correct/update_weights）")
print("  ray_evolution_relaxed.py  7 KB  — 寬鬆門檻版本（Sharpe>0.8）")
print("  ray_self_correct.py        9 KB  — 雙層 LLM 自我修正（1.5B初審 + 7B複審）")
print()
print("黃金挖掘")
print("  ray_gold_miner.py         11 KB  — 黃金案例挖掘（Sharpe>1.5）")
print()
print("蒸餾訓練")
print("  ray_train_tina.py         11 KB  — Unsloth 蒸餾訓練框架")
print("  step3_generate_jsonl.py   7 KB  — 生成 ray_distill_weekly.jsonl")
print("  step4_run_peft.py          5 KB  — Transformers PEFT 微調執行")
print("  step4_ollama_fallback.py   3 KB  — Ollama 被動蒸餾替代方案")
print("  step5_deploy_modelfile.py 5 KB  — Modelfile 更新（已執行）")
print()
print("每日自動化")
print("  tina_daily_self_correct.py 8 KB  — 每日盤後自動修正循環")
print("  tina_7b_warmup.py          1 KB  — 7B 預熱腳本（每日 07:50）")
print()
print("系統健檢")
print("  tina_health_check.py       9 KB  — 系統健康檢查（8/10 分）")
print("  slow_think_review.py       5 KB  — 慢思考檢討 + LLM 比例分析")
print("  isolated_jobs_review.py   6 KB  — Isolated Jobs 健檢報告")
print("  db_health_check.py         2 KB  — 資料庫健檢")
print()
print("掃描監控")
print("  us_momentum.py             6 KB  — 技術動能掃描（1D/5D/20D）")
print("  us_scan_live.py            5 KB  — 即時技術掃描（MA20/MA60/RSI/MACD/KDJ）")
print()
print("台股回測")
print("  taiwan_backtest.py        15 KB  — 台股 3-5 月回測（500檔）")
print()
print("AutoCAD 字體")
print("  filter_acad_fonts.py      6 KB  — 字體篩選工具")
print("  remove_acad_fonts.py       3 KB  — 字體移除腳本")
print()
print("【資料庫狀態】")
print()
print(f"  wisdom_logs:         {wl} 筆（失敗: {wl-wp} | 衰減: {lw} | 強化: {hw}）")
print(f"  wisdom_corrections: {wc} 筆（高信心: {g2}）")
print(f"  backtest_reports:    {br} 筆（Sharpe>0.8: {g1}）")
print(f"  signals_log:         {sl} 筆")
print()
print("【Ollama 模型】")
try:
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = r.json().get("models", [])
    for m in models:
        if "ray" in m["name"].lower() or "qwen" in m["name"].lower():
            mb = m.get("size", 0) // (1024**2)
            print(f"  {m['name']}: {mb:.0f} MB")
except:
    pass

print()
print("【蒸餾 Pipeline】")
print("  Step 1: 黃金案例挖掘     [DONE]  18 筆 Sharpe>0.8")
print("  Step 2: 7B 深度修正      [DONE]  144 筆 wisdom_corrections")
print("  Step 3: 生成 JSONL      [DONE]  29 筆 ray_distill_weekly.jsonl")
print("  Step 4: 微調訓練         [BLOCKED] triton 版本衝突")
print("  Step 5: 部署 Ollama      [DONE]  Modelfile 已更新（被動蒸餾）")

conn.close()