# -*- coding: utf-8 -*-
"""
ray_preload_0830.py — 08:30 開盤前預載腳本
使用 @ray_singleton_high_priority 確保 VRAM 乾淨+優先執行

用途：
  - 每日 08:30 開盤前預載 ray-v3.5 模型
  - 將最新 axioms/rules 載入 RAM
  - 確保 09:00 實戰時模型已就緒

使用 @ray_singleton_high_priority：
  - 獨立鎖（ray_vram_priority.lock），不與一般任務排隊
  - 60秒死鎖自動破門
  - 積極物理清理 VRAM
"""

import sys, os, time
from pathlib import Path

BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_guard import ray_singleton_high_priority, ray_guard_clear
except ImportError:
    print("[WARN] ray_guard not found, skipping protection")
    def ray_singleton_high_priority(func):
        return func

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False


@ray_singleton_high_priority
def preload_0830():
    """08:30 開盤前預載任務"""
    print("="*50)
    print("🚀 08:30 開盤前預載啟動")
    print(f"   時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Step 1: 預載模型至 VRAM
    if HAS_OLLAMA:
        print("\n[Step 1] 預載 ray-v3.5 至 VRAM...")
        try:
            t0 = time.time()
            # 輕量 warmup prompt
            response = ollama.generate(
                model="ray-v3.5",
                prompt="WARMUP_SESSION: 系統啟動，請確認就緒。",
                options={"temperature": 0.1, "num_predict": 20}
            )
            elapsed = time.time() - t0
            print(f"   ✅ ray-v3.5 預載完成 ({elapsed:.1f}s)")
        except Exception as e:
            print(f"   ⚠️ ray-v3.5 預載失敗: {e}")
            print("   系統將在 09:00 冷啟動，可能有延遲")
    
    # Step 2: 確保 locks 目錄存在
    lock_dir = BASE_DIR / "locks"
    lock_dir.mkdir(exist_ok=True)
    print(f"\n[Step 2] Lock 目錄: {lock_dir} ✅")
    
    # Step 3: 讀取並快取最新 axioms
    axioms_file = BASE_DIR / "stores" / "long_term" / "axioms_v3.5.json"
    semantic_file = BASE_DIR / "stores" / "long_term" / "semantic_logic_v2.json"
    forbidden_file = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
    
    cache = {}
    for name, f in [("axioms", axioms_file), ("semantic", semantic_file), ("forbidden", forbidden_file)]:
        if f.exists():
            try:
                import json
                cache[name] = json.loads(f.read_text(encoding="utf-8"))
                print(f"   📦 {name}: {len(str(cache[name]))} chars loaded")
            except Exception as e:
                print(f"   ⚠️ {name} 讀取失敗: {e}")
        else:
            print(f"   ⚠️ {name}: 檔案不存在 ({f.name})")
    
    print(f"\n✅ 預載完成，快取了 {len(cache)} 個規則檔案")
    print(f"   時間: {time.strftime('%H:%M:%S')}")
    print("="*50)
    
    return cache


if __name__ == "__main__":
    print("ray_preload_0830.py — 08:30 開盤前預載")
    print()
    try:
        result = preload_0830()
        print(f"\n🎯 預載任務完成，已就緒迎接 09:00 開盤")
    except Exception as e:
        print(f"\n❌ 預載任務失敗: {e}")
        print("嘗試手動清理鎖後重試...")
        try:
            ray_guard_clear()
        except:
            pass