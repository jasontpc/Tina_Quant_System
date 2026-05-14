# -*- coding: utf-8 -*-
"""
ray_idle_manager.py — 閒置時智力強化管線

觸發條件：系統閒置 8 分鐘（非交易時段）
保護：@market_safe_guard + @ray_singleton + @io_singleton
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scripts.utils.ray_guard import ray_singleton, market_safe_guard, io_singleton

IDLE_MINUTES = 8

def get_idle_seconds() -> int:
    """取得系統閒置秒數"""
    try:
        import ctypes, struct
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) // 1000
    except:
        return 0

@market_safe_guard
@ray_singleton
@io_singleton
def idle_evolution_pipeline():
    """閒置時智力強化管線"""
    print("🌙 Tina 偵測到系統閒置：啟動大師人格強化程序...")

    import subprocess
    scripts = [
        ("scripts/expand_lessons.py",    "Lessons/Patterns 擴充"),
        ("scripts/pattern_cross_logic.py", "交叉邏輯 Pattern"),
        ("scripts/ray_master_burn.py",    "Modelfile 固化燒錄"),
    ]

    results = []
    for script_path, desc in scripts:
        full = Path(__file__).parent / script_path
        if full.exists():
            try:
                r = subprocess.run(
                    ["python", str(full)],
                    capture_output=True, text=True, timeout=300
                )
                results.append(f"✅ {desc}")
            except Exception as e:
                results.append(f"⚠️ {desc}: {e}")
        else:
            results.append(f"⏭️ {desc} (不存在，跳過)")

    print("🌙 閒置重生完成：")
    for r in results:
        print(f"  {r}")
    return results

def main():
    idle_s = get_idle_seconds()
    idle_m = idle_s / 60
    print(f"[Idle Check] idle={idle_m:.1f}min (threshold={IDLE_MINUTES}min)")
    if idle_s >= IDLE_MINUTES * 60:
        print("✅ 閒置超標，啟動智力強化...")
        idle_evolution_pipeline()
    else:
        print(f"⏳ 閒置不足（{idle_m:.1f}min < {IDLE_MINUTES}min），退出")

if __name__ == "__main__":
    main()