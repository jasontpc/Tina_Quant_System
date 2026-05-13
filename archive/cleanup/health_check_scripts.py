# -*- coding: utf-8 -*-
"""健康檢查"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

scripts = [
    'ray_web_learner.py', 'ray_econ_learner.py', 'ray_web_distiller.py',
    'ray_token_tracker.py', 'ray_brain.py', 'ray_self_correct.py',
    'ray_distiller_auto.py', 'ray_retriever_v2.py', 'ray_integrity_booster.py',
    'ray_engine.py', 'ray_expert_modules.py', 'tina_daily_self_correct.py',
    'tina_health_check.py', 'ray_db_cleanup.py', 'slow_think_review.py'
]

print("腳本健檢結果：\n")
issues = []
for s in scripts:
    if not os.path.exists(s):
        print(f"❌ MISSING: {s}")
        issues.append(s)
        continue
    size = os.path.getsize(s)
    try:
        with open(s, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        lines = content.split('\n')
        # 檢查常見錯誤
        has_double_brace = '{{' in content or '}}' in content
        has_syntax_error = False
        try:
            compile(content, s, 'exec')
        except SyntaxError as e:
            has_syntax_error = True
            print(f"⚠️  SYNTAX: {s} -> {e}")
        # 檢查是否有 TODO 或 FIXME
        has_todo = 'TODO' in content or 'FIXME' in content
        status = "OK" if size > 500 else "SMALL"
        flags = []
        if has_double_brace: flags.append("⚠️ f-string escape")
        if has_syntax_error: flags.append("❌ syntax error")
        if has_todo: flags.append("📝 TODO")
        flag_str = " | ".join(flags) if flags else ""
        print(f"{'✅' if not flags else '⚠️ '} {status}: {s} ({size} bytes, {len(lines)} lines) {flag_str}")
    except Exception as e:
        print(f"❌ READ ERROR: {s} -> {e}")
        issues.append(s)

print(f"\n總計: {len(scripts)} 腳本, {len(issues)} 問題")
if not issues:
    print("✅ 所有腳本健檢通過")