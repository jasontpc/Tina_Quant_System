# -*- coding: utf-8 -*-
"""
ray_vram_cleaner.py — 單模型物理隔離守護者
確保只有目標模型運行，其餘全部物理清除

用法：
  python ray_vram_cleaner.py [model_name]
  python ray_vram_cleaner.py --force [model_name]  # 強制清除後啟動
"""
import subprocess, time, sys, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
_log = logging.getLogger("vram_cleaner")

ALL_MODELS = [
    "ray-v3.5",
    "qwen3.5-4b-iq4xs",
    "qwen3.5-4b-instruct-q4_K_S",
    "ray-deep-v1",
    "ray-commander",
    "qwen2.5:7b",
]
COOLDOWN = 5   # GPU 釋放緩衝秒數

def get_running_models():
    try:
        result = subprocess.run(["ollama", "list"],
                               capture_output=True, text=True, timeout=10, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        return [l.split()[0] for l in lines if l.strip() and not l.startswith("NAME")]
    except:
        return []

def get_vram_gb():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                           "--format=csv,noheader,nounits"],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return int(r.stdout.strip().split('\n')[0]) / 1024
    except:
        pass
    return None

def force_singleton_model(target_model, cooldown=COOLDOWN):
    """確保只有 target_model 運行（物理清除）"""
    _log.info(f"[CLEANER] 目標模型: {target_model}")
    running = get_running_models()
    _log.info(f"[CLEANER] 運行中: {running}")

    stopped = []
    for m in running:
        if m != target_model:
            try:
                subprocess.run(["ollama", "stop", m],
                              capture_output=True, timeout=30, check=False)
                stopped.append(m)
                _log.info(f"  ✓ 已停止: {m}")
            except Exception as e:
                _log.warning(f"  ✗ 停止失敗: {m} → {e}")

    _log.info(f"[CLEANER] 已清理 {len(stopped)} 個模型，{cooldown}s 冷卻...")
    time.sleep(cooldown)

    vram = get_vram_gb()
    _log.info(f"[CLEANER] VRAM: {vram:.1f}GB" if vram else "[CLEANER] VRAM: 無法讀取")

    # 驗證
    still_running = get_running_models()
    violation = [m for m in still_running if m != target_model]
    if violation:
        _log.warning(f"[CLEANER] ⚠️ 仍有模型殘留: {violation}")
        return False
    else:
        _log.info(f"[CLEANER] ✅ 單模型環境達成: {target_model}")
        return True

def query_vram_audit():
    """查詢 VRAM 違規記錄（從 vram_audit 表）"""
    try:
        import sqlite3, os
        db = os.path.join(os.path.dirname(__file__), "ray_wisdom.db")
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='vram_audit'")
        if c.fetchone()[0] == 0:
            print("[vram_audit] 表格不存在，跳過")
            conn.close()
            return
        c.execute("SELECT * FROM vram_audit ORDER BY timestamp DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()
        if rows:
            print("[vram_audit] 最近違規:")
            for r in rows:
                print(f"  {r}")
        else:
            print("[vram_audit] 無違規記錄")
    except Exception as e:
        print(f"[vram_audit] 查詢失敗: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None

    print("=== VRAM 單模型物理隔離守護者 ===")
    running = get_running_models()
    vram = get_vram_gb()
    print(f"VRAM: {vram:.1f}GB | Running: {running}")

    if target:
        ok = force_singleton_model(target)
        sys.exit(0 if ok else 1)
    else:
        # 無參數：顯示狀態並寫入 vram_audit（若存在）
        print("用法: python ray_vram_cleaner.py <model_name>")
        print(f"可用模型: {ALL_MODELS}")
        query_vram_audit()