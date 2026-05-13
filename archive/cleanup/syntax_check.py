# -*- coding: utf-8 -*-
"""深度語法檢查"""
import sys, os, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

scripts = [
    'ray_web_learner.py', 'ray_econ_learner.py', 'ray_web_distiller.py',
    'ray_brain.py', 'ray_self_correct.py', 'tina_daily_self_correct.py'
]

print("深度語法檢查：\n")
errors = []
for s in scripts:
    if not os.path.exists(s):
        print(f"❌ MISSING: {s}")
        errors.append(s)
        continue
    try:
        with open(s, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        compile(content, s, 'exec')
        print(f"✅ COMPILE OK: {s}")
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR: {s}")
        print(f"   Line {e.lineno}: {e.msg}")
        print(f"   Text: {e.text}")
        errors.append(s)
    except Exception as e:
        print(f"⚠️  ERROR: {s} -> {e}")
        errors.append(s)

print(f"\n結果: {len(scripts) - len(errors)}/{len(scripts)} 通過")
if errors:
    print(f"❌ 有 {len(errors)} 個腳本需要修復")