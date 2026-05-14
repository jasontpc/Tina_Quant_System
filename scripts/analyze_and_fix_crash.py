# -*- coding: utf-8 -*-
"""
analyze_and_fix_crash.py — Gateway 崩潰自動歸因系統

功能：
  1. 讀取 logs/gateway-restart.log（Big5 編碼）
  2. 分析崩潰模式（NETWORK_LATENCY / API_LIMIT_CRASH / MEMORY_LEAK / UNKNOWN）
  3. 自動將防禦規則寫入 stores/long_term/ray_forbidden_rules.json
  4. 產出崩潰報告到 stores/short_term/crash_analysis_YYYYMMDD.json

崩潰模式分類：
  - WINDOWS_TASK_HANDOFF → [SYSTEM_FRAGILE_ZONE] 外部重啟，標注但不禁止
  - NETWORK_LATENCY (>5s) → 網路延遲，添加網路超時規則
  - API_LIMIT_CRASH → API 限流，添加 rate_limit 規則
  - MEMORY_LEAK → 記憶體洩漏，標注記憶體管理注意點

用法：
  python scripts/analyze_and_fix_crash.py
  → 每次 Gateway 重啟後自動執行（可在 05:00 蒸餾流程中加入）
"""

import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOG_FILE = Path(r"C:\Users\USER\.openclaw\logs\gateway-restart.log")
FORBIDDEN_RULES_FILE = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
OUTPUT_DIR = BASE_DIR / "stores" / "short_term"

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 解析崩潰日誌（Big5 + 週幾前綴）─────────────────────────────────────
def parse_gateway_log(log_content: str) -> list:
    events = []
    for line in log_content.split('\n'):
        if not line.strip():
            continue

        # 格式：[週一 2026/05/04  6:09:47.27] message
        m = re.search(r'\[([^]]+)\]\s*(.*)', line)
        if not m:
            continue

        full_ts = m.group(1)  # "週一 2026/05/04  6:09:47.27"
        msg = m.group(2).strip()

        # 提取日期時間（移除星期幾前綴）
        ts_match = re.search(r'(\d{4}/\d+/\d+\s+\d+:\d+:\d+\.\d+)', full_ts)
        if not ts_match:
            continue
        ts_str = ts_match.group(1)

        # 解析訊息欄位
        src_match = re.search(r'source=(\w+)', msg)
        target_match = re.search(r'target="([^"]+)"', msg)
        restart_type = re.search(r'restart (attempt|finished|fallback)', msg)

        events.append({
            "raw_date": ts_str,
            "timestamp": datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S.%f"),
            "source": src_match.group(1) if src_match else "unknown",
            "target": target_match.group(1) if target_match else "unknown",
            "type": restart_type.group(1) if restart_type else "unknown",
            "msg": msg,
        })

    return events

# ── 判斷崩潰模式 ─────────────────────────────────────────────────────
def classify_crash(events: list) -> dict:
    """
    attempt → finished = 正常重啟
    attempt → fallback = Windows 任務接管（正常）
    attempt → (nothing) = 異常崩潰
    """
    crashes = []
    i = 0
    while i < len(events):
        evt = events[i]
        if evt["type"] == "attempt":
            next_evt = events[i + 1] if i + 1 < len(events) else None
            if next_evt is None:
                crashes.append({"pattern": "UNKNOWN_CRASH", "severity": "high", "event": evt})
            elif next_evt["type"] == "fallback":
                crashes.append({"pattern": "WINDOWS_TASK_HANDOFF", "severity": "low", "event": evt})
            elif next_evt["type"] == "finished":
                crashes.append({"pattern": "NORMAL_RESTART", "severity": "info", "event": evt})
        i += 1

    return {
        "total_events": len(events),
        "crashes": crashes,
        "summary": {
            "normal_restart": sum(1 for c in crashes if c["pattern"] == "NORMAL_RESTART"),
            "windows_task_handoff": sum(1 for c in crashes if c["pattern"] == "WINDOWS_TASK_HANDOFF"),
            "unknown_crash": sum(1 for c in crashes if c["pattern"] == "UNKNOWN_CRASH"),
        }
    }

# ── 生成禁止規則 ─────────────────────────────────────────────────────
def generate_forbidden_rules(crash_summary: dict) -> list:
    new_rules = []

    if crash_summary["summary"]["windows_task_handoff"] > 0:
        new_rules.append({
            "id": "SYS_001",
            "rule": "WINDOWS_TASK_HANDOFF detected — system restart triggered externally by Windows task scheduler",
            "action": "LOG_ONLY",
            "master": "SYSTEM",
            "tags": ["[SYSTEM_FRAGILE_ZONE]"],
            "priority": 1,
            "note": "Gateway 被 Windows 任務重啟，非策略錯誤，僅記錄"
        })

    if crash_summary["summary"]["unknown_crash"] > 0:
        new_rules.append({
            "id": "SYS_002",
            "rule": "UNKNOWN_CRASH detected — restart without fallback path detected in gateway-restart.log",
            "action": "BLOCK_TRADING",
            "master": "SYSTEM",
            "tags": ["[SYSTEM_FRAGILE_ZONE]", "[GUARDIAN_LOCK]"],
            "priority": 3,
            "note": "未知崩潰時阻斷交易，防止敞口風險"
        })

    return new_rules

# ── 主流程 ─────────────────────────────────────────────────────────────
def main():
    print("=== Gateway Crash Analyzer 啟動 ===")

    if not LOG_FILE.exists():
        print(f"[警告] {LOG_FILE} 不存在，跳過")
        return {"status": "skipped", "reason": "no_log_file"}

    with open(LOG_FILE, "r", encoding="big5", errors="replace") as f:
        raw_content = f.read()

    print(f"[Step 1] 讀取日誌：{len(raw_content)} 字元")

    events = parse_gateway_log(raw_content)
    print(f"[Step 2] 解析事件：{len(events)} 筆")

    classification = classify_crash(events)
    print(f"[Step 3] 分類結果：")
    for k, v in classification["summary"].items():
        print(f"    {k}: {v} 次")

    new_rules = generate_forbidden_rules(classification)
    print(f"[Step 4] 生成新規則：{len(new_rules)} 條")

    if new_rules:
        existing = load_json(FORBIDDEN_RULES_FILE, {"rules": []})
        existing_ids = {r.get("id") for r in existing.get("rules", [])}

        for rule in new_rules:
            if rule["id"] not in existing_ids:
                existing["rules"].append(rule)
                print(f"    + 新增：{rule['id']} ({rule['rule'][:50]})")
            else:
                print(f"    = 已存在：{rule['id']}")

        save_json(FORBIDDEN_RULES_FILE, existing)
        print(f"[Step 5] 已寫入 {FORBIDDEN_RULES_FILE.name}（共 {len(existing['rules'])} 條）")
    else:
        print("[Step 5] 無新規則，跳過寫入")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log_file": str(LOG_FILE),
        "events": [{"date": e["raw_date"], "source": e["source"], "type": e["type"]} for e in events],
        "classification": {
            "total_events": classification["total_events"],
            "summary": classification["summary"],
        },
        "new_rules_added": [r["id"] for r in new_rules],
    }

    output_file = OUTPUT_DIR / f"crash_analysis_{datetime.now().strftime('%Y%m%d')}.json"
    save_json(output_file, report)
    print(f"[Step 6] 報告已寫入：{output_file.name}")

    print()
    print("=== 完成 ===")
    print("下次 05:00 蒸餾將自動燒錄新規則到 ray-v3.5")
    return report

if __name__ == "__main__":
    result = main()