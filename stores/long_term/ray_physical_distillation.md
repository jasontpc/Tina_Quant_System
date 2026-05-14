# Ray System 物理級 Modelfile 固化方案
> 建立：2026-05-13 16:40

---

## 核心理念

> 利用 7B 參謀在後方壓縮智力，再將精華「強行寫入」4B 指揮官的基因。

RTX 4050 6GB 限制下，所有複雜微調簡化為「物理級 Modelfile 固化」。

---

## 🧠 1. 暴力訓練：7B 智力壓縮提示詞 (14:00 - 17:00)
**執行模型：** qwen2.5:7b 或 ray-deep-v1

```
### ROLE: MASTER LOGIC DISTILLER ###
[Task]: 深度分析今日錯誤日誌、67 筆歷史修正與產業鏈連網數據。
[Constraint]:
1. 僅保留具備統計優勢的規律。
2. 對齊 Taleb (反脆弱) 與 Thorp (資金紀律)。
3. 禁止禮貌用語，禁止解釋。
[Output Format]: 輸出極簡 JSON 陣列，標籤為 "axioms_v3.5"。
[Mission]: 產出 10 條 4B 指揮官必須遵守的絕對「If-Then」禁令。
[Example]: {"if": "RSI2 > 90 AND Volume_Ratio < 1.0", "then": "SELL", "reason": "Taleb_Risk"}
```

**位置：** `ray_knowledge_distiller.py` / `ray_logic_distiller.py`

---

## ⚡ 2. 物理灌頂：4B 模型固化腳本 (05:00)
**腳本：** `ray_distiller_auto.py`

```python
def brute_force_rebuild():
    # 1. 物理清理：確保顯存絕對乾淨，避免 OOM
    subprocess.run(["ollama", "stop", "qwen2.5:7b"])
    subprocess.run(["ollama", "stop", "ray-deep-v1"])

    # 2. 讀取昨日 7B 蒸餾出的最高天條 (axioms_v3.5.json)
    try:
        with open('axioms_v3.5.json', 'r', encoding='utf-8') as f:
            axioms = f.read()
    except FileNotFoundError:
        axioms = "保持冷靜，執行 Connors RSI2 策略。"

    # 3. 暴力構建 Modelfile
    modelfile_content = f"""
FROM qwen3.5:4b-instruct-q4_K_S
PARAMETER temperature 0.1
PARAMETER num_ctx 8192
SYSTEM \"\"\"
你是 Ray-v3.5 實戰指揮官。你沒有自我，只有固化在基因裡的絕對天條：
{axioms}
[Master Persona]:
- Taleb: 優先活下去。
- Thorp: 算準部位紀律。
- Connors: RSI2 均值回歸。
[Execution]:
- 信心值 < 0.8 時，輸出 Action: WAIT 並請求 MiniMax 覆核。
- 嚴格 JSON 輸出，禁止廢話。
\"\"\"
"""
    # 4. 暴力重新生成模型
    subprocess.run(["ollama", "create", "ray-v3.5", "-f", "Ray-v3.5.Modelfile"])
```

---

## 🛡️ 3. 資源守護：單模型互斥調度 (全天候)

```python
def clear_vram_and_run(target_model):
    """確保顯存只有單一模型，避免 4050 崩潰"""
    all_models = ["ray-v3.5", "qwen2.5:7b", "ray-deep-v1"]
    for m in all_models:
        if m != target_model:
            subprocess.run(["ollama", "stop", m])
    import time
    time.sleep(3)
```

**已實作：** `ray_scheduler.py` 的 `clear_vram()` / `clear_vram_full()`

---

## 📊 整合優化重點

| 優化 | 預期效果 |
|:-----|:---------|
| **Token 減肥** | No Prose 指令，節省 15% Token，nl2code 解析成功率提升 |
| **信心降級** | 4B 指令：Confidence < 0.8 → 求助 MiniMax，保護 6GB VRAM |
| **RAM 替代推理** | 產業鏈映射存入 32GB RAM，4B 實戰只需「查表」，速度 +300% |

---

## 🔄 每日固化迴圈

```
14:00 ── 7B 蒸餾 ──→ axioms_v3.5.json
              ↓
05:00 ── 物理灌頂 ──→ ray-v3.5.Modelfile
              ↓
09:00 ── 4B 實戰指揮 ──→ scan_and_propose()
              ↓
14:00 ── 蒸餾新天條 ──→ (Loop)
```

---

_建立：2026-05-13 16:40_