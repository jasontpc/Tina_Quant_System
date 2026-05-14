# -*- coding: utf-8 -*-
"""
ray_self_fixer.py — 邏輯自動修正引擎
14:10 執行（緊接在 ray-deep-v1 蒸餾後）

流程：
  1. 讀取 system_fault_logs（今日報錯）
  2. 調用 ray-deep-v1 生成修正邏輯
  3. 存入 logic_corrections（供 05:00 固化使用）
  4. 若嚴重錯誤，寫入 system_fault_logs.fixed + 生成修復腳本
"""
import sys, os, sqlite3, json, time
import subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENTS_DIR, "ray_wisdom.db")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "ray-deep-v1"

def ollama_generate(model, prompt, temperature=0.15, num_predict=300, timeout=90):
    try:
        import requests
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0.8, "num_predict": num_predict}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def log_fault(script, error_type, traceback, fix_script=None):
    """寫入 system_fault_logs"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""INSERT INTO system_fault_logs (script_name, error_type, traceback, fix_script)
                  VALUES (?, ?, ?, ?)""", (script, error_type, traceback, fix_script))
    conn.commit()
    conn.close()

def get_unfixed_faults():
    """讀取未修復的錯誤"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT id, script_name, error_type, traceback, timestamp
                 FROM system_fault_logs WHERE fixed=0 ORDER BY timestamp DESC LIMIT 10""")
    rows = c.fetchall()
    conn.close()
    return rows

def save_logic_correction(failed_logic, fixed_logic, master_tag, confidence=0.75):
    """存入 logic_corrections（新天條）"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""INSERT INTO logic_corrections (failed_logic, fixed_logic, master_tag, confidence)
                  VALUES (?, ?, ?, ?)""", (failed_logic, fixed_logic, master_tag, confidence))
    conn.commit()
    conn.close()

def mark_fixed(fault_id, fix_script=None):
    """標記為已修復"""
    from datetime import datetime
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""UPDATE system_fault_logs
                 SET fixed=1, fix_script=?, resolved_at=?
                 WHERE id=?""", (fix_script, datetime.now().strftime("%Y-%m-%d %H:%M"), fault_id))
    conn.commit()
    conn.close()

def fix_script_logic(script_name, error_type, traceback, fault_id=None):
    """調用 ray-deep-v1 生成修正邏輯"""
    prompt = f"""### ROLE: RAY LOGIC REPAIR ENGINE ###
[Task]: 分析以下系統錯誤並生成「修復後的新邏輯」，存入 logic_corrections 供日後固化。

錯誤腳本: {script_name}
錯誤類型: {error_type}
堆疊追蹤:
{traceback}

請分析並產出（JSON）：
{{
  "failed_logic": "原本為何錯誤（一句話）",
  "fixed_logic": "修復後的正確邏輯（具體描述）",
  "confidence": 0.0-1.0（修復信心），
  "master_tag": "ray-deep-v1:YYYYMMDD"
}}

只輸出 JSON，嚴禁其他文字。"""

    result = ollama_generate(MODEL, prompt)
    if result and "ERROR" not in result:
        try:
            data = json.loads(result)
            save_logic_correction(
                failed_logic=data.get("failed_logic", ""),
                fixed_logic=data.get("fixed_logic", ""),
                master_tag=data.get("master_tag", f"{MODEL}:20260513"),
                confidence=data.get("confidence", 0.75)
            )
            print(f"[+] 修正邏輯已存入 logic_corrections")
            if fault_id is not None:
                mark_fixed(fault_id, fix_script=result)
            return True
        except json.JSONDecodeError:
            print(f"[-] 無法解析 JSON: {result[:200]}")
    else:
        print(f"[-] ray-deep-v1 修正失敗: {result[:200]}")
    return False

# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(" 14:10 邏輯自動修正引擎（ray-deep-v1）")
    print(f" Time: {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 前置清理：確保 VRAM 乾淨（單模型協議）
    print("[VRAM] 執行任務前清理...")
    try:
        subprocess.run(["ollama", "stop", "--all"],
                       capture_output=True, timeout=60, check=False)
        time.sleep(60)
    except:
        pass

    faults = get_unfixed_faults()
    if not faults:
        print("[+] system_fault_logs 無未修復錯誤")
    else:
        print(f"[*] 發現 {len(faults)} 個未修復錯誤，開始修正...")
        for fault_id, script, err_type, tb, ts in faults:
            print(f"\n  [{fault_id}] {script} — {err_type}")
            ok = fix_script_logic(script, err_type, tb[:500], fault_id)
            print(f"  → {'✅ 已修正' if ok else '❌ 失敗'}")

    # 若無錯誤，也寫入一筆正常運行的健康檢查
    if not faults:
        print("[+] 全系統健康，寫入正常狀態")
        log_fault("ray_self_fixer.py", "HEALTH_CHECK",
                  "14:10 執行，全系統正常，無錯誤", None)

    # 任務結束：卸載模型
    try:
        subprocess.run(["ollama", "stop", MODEL],
                       capture_output=True, timeout=30, check=False)
    except:
        pass

    print("=" * 60)

if __name__ == "__main__":
    main()