# -*- coding: utf-8 -*-
"""
ray_semantic_auto.py — 全語意標籤固化重生（05:00執行）

功能：
1. 讀取 semantic_logic_v2.json（純語意標籤規則）
2. 構建 Ray-Commander.Modelfile（無數字，純標籤基因）
3. ollama create ray-v3.5 物理燒錄
4. 驗證模型正常運行

整合：@ray_singleton（顯存鎖） + @io_singleton（日誌保護）
"""

import subprocess, os, json, time, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SEMANTIC_FILE = BASE_DIR / "stores" / "long_term" / "semantic_logic_v2.json"
MODELFILE_PATH = BASE_DIR / "Ray-Commander.Modelfile"
LOG_FILE = BASE_DIR / "stores" / "distillation_log.json"

try:
    sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))
    from ray_guard import ray_singleton
    from ray_io_guard import io_singleton
except ImportError:
    def ray_singleton(fn): return fn
    def io_singleton(fn): return fn

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@ray_singleton
def pure_semantic_rebuild():
    print("=== Ray Semantic Auto-Rebuild 啟動（05:00）===")
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": []}

    # Step 1: 讀取語意規則
    try:
        with open(SEMANTIC_FILE, "r", encoding="utf-8") as f:
            semantic_data = json.load(f)
        rules = semantic_data.get("rules", [])
        semantic_logic = json.dumps(semantic_data, ensure_ascii=False)
        print(f"[Step 1] 讀取語意規則：{len(rules)} 條")
        log["steps"].append({"step": "load_semantic", "count": len(rules)})
    except FileNotFoundError:
        rules = []
        semantic_logic = "[DEFAULT_SEMANTIC_LOGIC_ONLY]"
        print("[Step 1] 無語意規則檔案，使用預設")
        log["steps"].append({"step": "load_semantic", "note": "not_found"})

    # Step 2: 構建 Modelfile（SYSTEM 部分用雙引號包圍）
    system_prompt = (
        '你是 Ray-v3.5 語意指揮官。\n'
        '你的判斷完全基於「標籤權重」，嚴禁處理具體數字。\n\n'
        '[固化語意邏輯庫]:\n' + semantic_logic + '\n\n'
        '[執行準則]:\n'
        '- 嚴禁處理具體數字，僅根據輸入的 [標籤組合] 進行推論。\n'
        '- 看到 [OVERHEATED] → 觸發減倉引導\n'
        '- 看到 [VOL_PRICE_DIVERGENCE] → 視為 [TRAP]\n'
        '- 看到 [ANTIFRAGILE] → 信心評定為 HIGH\n'
        '- 看到 [BLACK_SWAN_RISK] → 全面觀望\n\n'
        '[分析後必須給出選擇]:\n'
        '[A] 執行指令\n'
        '[B] 略過（No Op）\n'
        '[C] 深度歸因'
    )

    modelfile_content = (
        "FROM qwen3.5:4b-instruct-q4_K_S\n"
        "PARAMETER temperature 0.1\n"
        "PARAMETER num_predict 512\n"
        "PARAMETER top_p 0.85\n"
        "PARAMETER top_k 20\n"
        "SYSTEM \"" + system_prompt.replace('"', '\\"').replace('\n', '\\n') + "\"\n"
    )

    with open(MODELFILE_PATH, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    print(f"[Step 2] 構建 Modelfile：{len(modelfile_content)} 字元")
    log["steps"].append({"step": "build_modelfile", "size": len(modelfile_content)})

    # Step 3: ollama create
    print("[Step 3] ollama create ray-v3.5...")
    try:
        result = subprocess.run(
            ["ollama", "create", "ray-v3.5", "-f", str(MODELFILE_PATH)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("[Step 3] 模型創建成功")
            log["steps"].append({"step": "ollama_create", "status": "ok"})
        else:
            err = result.stderr[:200] if result.stderr else "unknown"
            print(f"[Step 3] 模型創建失敗：{err}")
            log["steps"].append({"step": "ollama_create", "status": "error", "msg": err})
    except Exception as e:
        print(f"[Step 3] exception: {e}")
        log["steps"].append({"step": "ollama_create", "status": "exception", "msg": str(e)})

    # Step 4: 驗證
    try:
        check = subprocess.run(
            ["ollama", "run", "ray-v3.5", "test"],
            capture_output=True, text=True, timeout=30
        )
        status = "ok" if check.returncode == 0 else "warn"
        print(f"[Step 4] 驗證：{status}")
        log["steps"].append({"step": "verify", "status": status})
    except:
        print("[Step 4] 驗證跳過")
        log["steps"].append({"step": "verify", "status": "skipped"})

    # Step 5: 日誌
    log["completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
    log["rules_loaded"] = len(rules)
    log_entries = load_json(LOG_FILE, [])
    log_entries.append(log)
    save_json(LOG_FILE, log_entries[-10:])

    print(f"\n=== 全語意標籤化重生完成 ===")
    print(f"規則數：{len(rules)}")
    print(f"Modelfile：{MODELFILE_PATH.name}")
    print(f"模型：ray-v3.5")
    return {"rules": len(rules), "status": "ok"}

if __name__ == "__main__":
    result = pure_semantic_rebuild()
    print(f"\n燒錄結果：{result}")