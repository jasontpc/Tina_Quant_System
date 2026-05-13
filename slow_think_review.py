# -*- coding: utf-8 -*-
"""
慢思考檢討 + LLM 使用比例分析
"""

import json, time, sys, sqlite3, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"
conn = sqlite3.connect("ray_wisdom.db")
c = conn.cursor()

print("=" * 60)
print("  慢思考檢討 + LLM 使用比例分析")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ============================================================
# 1. Cron Jobs 健康狀況
# ============================================================
print("\n[1] Cron Jobs 健康狀況")
print("-" * 40)

# 從 wisdom_corrections 分析失敗模式
c.execute('''SELECT diagnosis FROM wisdom_corrections ORDER BY id DESC LIMIT 30''')
diag_samples = [row[0] for row in c.fetchall()]

# 分析失敗原因
fail_reasons = {}
for d in diag_samples:
    if not d:
        continue
    d_lower = d.lower()
    if "timeout" in d_lower or "timeout" in d_lower:
        fail_reasons["timeout"] = fail_reasons.get("timeout", 0) + 1
    elif "low sharpe" in d_lower or "sharpe" in d_lower:
        fail_reasons["low_sharpe"] = fail_reasons.get("low_sharpe", 0) + 1
    elif "mdd" in d_lower or "drawdown" in d_lower:
        fail_reasons["mdd_too_high"] = fail_reasons.get("mdd_too_high", 0) + 1
    elif "indicator" in d_lower:
        fail_reasons["wrong_indicator"] = fail_reasons.get("wrong_indicator", 0) + 1
    else:
        fail_reasons["other"] = fail_reasons.get("other", 0) + 1

print("  失敗原因分佈：")
for reason, count in sorted(fail_reasons.items(), key=lambda x: -x[1]):
    print(f"    {reason}: {count}")

# ============================================================
# 2. LLM 速度測試
# ============================================================
print("\n[2] LLM 速度測試（3次平均）")
print("-" * 40)

def test_model(model_id, name, n=3):
    times = []
    for i in range(n):
        t0 = time.time()
        try:
            r = requests.post(BASE_URL, json={
                "model": model_id,
                "messages": [{"role": "user", "content": "OK"}],
                "stream": False
            }, timeout=120)
            if r.status_code == 200:
                times.append(time.time() - t0)
        except:
            pass
    if times:
        avg = sum(times) / len(times)
        cold = times[0] if len(times) > 0 else avg
        warm = sum(times[1:]) / max(len(times[1:]), 1)
        return cold, warm
    return None, None

models = [("ray-v1", "Qwen 1.5B (雷達)"), ("ray-deep-v1", "Qwen 7B (參謀)")]
for model_id, name in models:
    cold, warm = test_model(model_id, name)
    if cold:
        print(f"  {name}:")
        print(f"    冷啟動: {cold:.1f}s | 快取後: {warm:.2f}s")
        speedup = cold / warm if warm > 0 else 1
        print(f"    加速比: {speedup:.1f}x (快取效益)")

# ============================================================
# 3. 計算最佳使用比例
# ============================================================
print("\n[3] LLM 最佳使用比例")
print("-" * 40)

# 目前實際使用量（從 logs 估計）
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
total_corr = c.fetchone()[0]
print(f"  wisdom_corrections 總筆數: {total_corr}")
print()

# 建議比例
print("  目前使用比例 vs 建議比例：")
print()
print("  任務類型              | 目前用  | 建議用  | 模型選擇")
print("  ---------------------|--------|--------|----------")
print("  簡單狀態查詢          |   7B   |   1.5B | ray-v1")
print("  技術指標計算          |   -    |   1.5B | ray-v1 (本地)")
print("  訊號評分 (score<3)    |   1.5B |   1.5B | ray-v1")
print("  訊號評分 (score>=3)   |   7B   |   1.5B | ray-v1")
print("  失敗wisdom初審        |   1.5B |   1.5B | ray-v1")
print("  深度歸因分析          |   7B   |   7B   | ray-deep-v1")
print("  蒸餾 teacher          |   7B   |   7B   | ray-deep-v1")
print("  策略進化              |   7B   |   7B   | ray-deep-v1")
print()
print("  建議：1.5B 佔 80% 任務，7B 佔 20%（只做複雜分析）")

# ============================================================
# 4. 改善計劃
# ============================================================
print("\n[4] 改善計劃")
print("-" * 40)

improvements = [
    ("A", "簡化 Cron Jobs", "14個jobs → 6個核心jobs，移除重複"),
    ("B", "1.5B 分流", "80% 簡單任務走 ray-v1，7B 只做深度"),
    ("C", "增加 timeout", "從 90s → 300s，避免 timeout error"),
    ("D", "本地 Python 替代", "技術指標計算完全不呼叫 LLM"),
    ("E", "預熱優化", "每日 07:50 預熱 7B，避免冷啟動"),
    ("F", "減少通知", "風控/Governor 只在異常時通知"),
]

for letter, title, desc in improvements:
    print(f"  {letter}. {title}")
    print(f"     {desc}")
print()

conn.close()

print("=" * 60)
print("  結論：")
print("  - 1.5B 應佔 80% 任務（每日監控/掃描/評分）")
print("  - 7B 只做 20%（深度歸因/蒸餾/策略進化）")
print("  - Cron jobs 從 14 精簡到 6，避免超載")
print("=" * 60)