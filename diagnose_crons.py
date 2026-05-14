#!/usr/bin/env python3
import json, subprocess, sys

CRONS = [
    ("56da375e", "56da375e-3e44-497d-9a6c-e5f6e4b49351", "US Margin 每日分析", 180),
    ("6bd43d57", "6bd43d57-e17c-4795-828f-c69b5174f9e0", "Ray 全語意固化重生（05:00）", 600),
    ("69734111", "69734111-6109-4fa8-9ed6-6b5e696bd99d", "Tina MEMORY 每日蒸餾", 300),
    ("30492325", "30492325-60ed-499d-8978-9a3d3e13b65b", "08:30 開盤前 RAM 預載", 180),
    ("57dfae5d", "57dfae5d-3795-4daf-916d-02fe4ccaa9d0", "Leo 台股波段每日分析", 420),
    ("d824a2bb", "d824a2bb-a4ba-4d6f-8119-9e7b945deb6e", "Tina 自主決策五大層", 600),
    ("f87364d8", "f87364d8-d946-426c-89e4-1136cc0385ea", "Ray 全語意蒸餾（14:00）", 900),
    ("2ebf42c9", "2ebf42c9-2a06-4527-8261-f7a62ef682c8", "14:05 失敗歸因蒸餾", 300),
]

print("=== Cron Job Timeout 診斷 ===\n")
fixes = []
for short, full_id, name, current_timeout in CRONS:
    try:
        r = subprocess.run(
            ["powershell", "-Command", f"openclaw cron runs --id {full_id} --limit 1"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(r.stdout)
        entries = data.get("entries", [])
        if entries:
            e = entries[0]
            dur_ms = e["durationMs"]
            dur_s = dur_ms / 1000
            dur_min = dur_s / 60
            status = e.get("status", "?")
            action = e.get("action", "?")
            # Recommendation
            if dur_s > current_timeout:
                new_timeout = int(dur_s * 1.5)
                rec = f"timeout {current_timeout}s -> {new_timeout}s（實際{dur_min:.1f}min）"
                fixes.append((short, new_timeout, name))
            elif dur_s > current_timeout * 0.7:
                new_timeout = int(dur_s * 1.3)
                rec = f"timeout {current_timeout}s -> {new_timeout}s（實際{dur_min:.1f}min）"
                fixes.append((short, new_timeout, name))
            else:
                new_timeout = current_timeout
                rec = f"OK（實際{dur_min:.1f}min，timeout={current_timeout}s）"
            print(f"[{short}] {name}")
            print(f"  actual: {dur_min:.1f}min | status: {status}/{action}")
            print(f"  {rec}")
            print()
        else:
            print(f"[{short}] {name} — 無記錄\n")
    except Exception as ex:
        print(f"[{short}] {name} — ERROR: {ex}\n")

print("=== 修復方案 ===")
for short, new_timeout, name in fixes:
    print(f"openclaw cron edit {short} --timeout {new_timeout}  # {name}")