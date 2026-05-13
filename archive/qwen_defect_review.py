# -*- coding: utf-8 -*-
"""
Ray 本地 Qwen 缺陷檢討與改善計劃
分析 ray-v1 (1.5B) 和 ray-deep-v1 (7B) 的具體缺陷與改善方案
"""

import sys, json, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"

print("=" * 60)
print("Ray 本地 Qwen 缺陷檢討與改善計劃")
print(f"時間：{time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

# ============================================================
# 缺陷分析
# ============================================================

print("【缺陷分析】")
print()

defects = [
    ("D1", "無主動蒸餾（權重更新）", "Step 4 微調受阻，triton 版本衝突", "高", "被動蒸餾（Modelfile）+ RAG 替代"),
    ("D2", "冷啟動延遲", "Ollama 模型載入慢，07:50 預熱可能不足", "中", "延長預熱時間 + 持久化熱模型"),
    ("D3", "上下文窗口有限", "1.5B context 4096 tokens，無法處理長歷史", "中", "壓縮歷史數據 + 分塊處理"),
    ("D4", "RAG 檢索質量不足", "wisdom_corrections 147 筆，高信心僅 21 筆", "中", "擴充案例庫 + 品質過濾"),
    ("D5", "雙語翻譯不完整", "Modelfile 中文化 11.2%，其餘仍英文", "低", "持續優化 Modelfile 雙語比例"),
    ("D6", "對抗校準觸發率低", "confidence < 0.5 才觸發 7B，多數繞過", "中", "降低閾值或增加其他觸發條件"),
    ("D7", "NL2Code 格式修復", "validator 可能過度寬容，接受了不良輸出", "中", "嚴格化校驗規則"),
]

for d_id, name, desc, severity, solution in defects:
    print(f"  {d_id}. {name}")
    print(f"      現況：{desc}")
    print(f"      嚴重性：{severity} | 對策：{solution}")
    print()

# ============================================================
# 改善計劃
# ============================================================

print("【改善計劃】")
print()

improvements = [
    ("I1", "預熱優化", "強化 tina_7b_warmup.py，增加模型熱身時間",
     "立即", "tina_7b_warmup.py 增加 2 分鐘熱身迴圈"),
    ("I2", "RAG 品質提升", "目標：wisdom_corrections 擴充至 300+ 筆，高信心 50+",
     "短期", "tina_daily_self_correct.py 增加案例寫入"),
    ("I3", "對抗校準閾值調整", "confidence < 0.7 觸發 7B（從 0.5 提高）",
     "立即", "修改 ray_brain.py co_inference 閾值"),
    ("I4", "NL2Code 嚴格化", "停損默認值 0.08 → None（必須明確指定）",
     "短期", "修改 ray_nl2code.py 填值邏輯"),
    ("I5", "雙語持續優化", "Modelfile 中文比例提升至 20%",
     "中期", "dynamic_modelfile_generator.py 增加中文內容"),
    ("I6", "Context 壓縮", "壓縮歷史數據至 2048 tokens 以內",
     "中期", "ray_brain.py 增加壓縮邏輯"),
    ("I7", "Docker 隔離微調", "容器化 PyTorch 2.5 + Triton 3.0",
     "長期", "建立 stable 訓練環境（待 PyTorch 修復）"),
]

for i_id, name, desc, timeline, action in improvements:
    print(f"  {i_id}. {name}（{timeline}）")
    print(f"      目標：{desc}")
    print(f"      行動：{action}")
    print()

# ============================================================
# 立即執行項目
# ============================================================

print("【立即執行】")
print()

immediate = [
    ("I3", "降低對抗校準閾值 0.5 → 0.7", "ray_brain.py co_inference threshold"),
]

for i_id, name, action_desc in immediate:
    print(f"  ▶ {name}")
    print(f"    行動：{action_desc}")
    print()

# ============================================================
# 測試 Ollama 延遲
# ============================================================

print("【Ollama 模型延遲測試】")
print()

models_to_test = [
    ("ray-v1", "1.5B 快速測試"),
    ("ray-deep-v1", "7B 深度測試"),
]

for model, desc in models_to_test:
    try:
        start = time.time()
        resp = requests.post(BASE_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": "NVDA"}],
            "stream": False
        }, timeout=60)
        elapsed = time.time() - start
        content = resp.json().get("message", {}).get("content", "")[:50].replace('\n', ' ')
        print(f"  {model}: {elapsed:.1f}s | 回應: {content}")
    except Exception as e:
        print(f"  {model}: 錯誤 - {str(e)[:50]}")

print()
print("=" * 60)
print("結論：Ray 本地 Qwen 系統已建立被動蒸餾 + RAG + 對抗校準")
print("核心限制：無主動蒸餾（Step 4 阻塞）→ 以被動蒸餾替代")
print("建議：優先執行 I3（對抗校準閾值調整）")
print("=" * 60)