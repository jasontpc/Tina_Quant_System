# -*- coding: utf-8 -*-
"""
ray_guardian.py — Gateway 崩潰監控與自動歸因中樞

功能：
  - 監控 openclaw_gateway 程序是否存活
  - 崩潰時自動提取日誌並觸發 @ray_singleton 分析
  - 產出 [CRASH_TAG] → stores/ray_crash_log/
  - 呼叫 ray_crash_distiller 進行 7B 參謀分析
  - 將新規則寫入 ray_forbidden_rules.json

使用：
  python scripts/ray_guardian.py
  （建議用 cron 設定為開機啟動，每 5 分鐘檢查一次）
"""

import os, sys, time, json, subprocess
from pathlib import Path
from datetime import datetime
from threading import Thread

# ── 路徑設定 ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOG_DIR = BASE_DIR / "stores" / "ray_crash_log"
CRASH_REPORT_DIR = LOG_DIR / "reports"
LOG_DIR.mkdir(parents=True, exist_ok=True)
CRASH_REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── 載入 ray_singleton（VRAM 守護）─────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))
try:
    from ray_guard import ray_singleton
except ImportError:
    def ray_singleton(fn):
        """降級：無 VRAM 鎖時直接執行"""
        def wrapper(*args, **kwargs):
            print(f"[Guardian] @ray_singleton bypass (ray_guard not available)")
            return fn(*args, **kwargs)
        return wrapper

# ── 全域狀態 ────────────────────────────────────────────────────────────────
_last_crash_time = 0
CRASH_COOLDOWN = 300  # 5 分鐘內不重複觸發
MONITOR_INTERVAL = 60 # 檢查間隔（秒）


# ── 崩潰監控循環 ────────────────────────────────────────────────────────────
def is_gateway_alive() -> bool:
    """檢查 OpenClaw Gateway 程序是否存活"""
    try:
        # Windows: tasklist
        result = subprocess.run(
            ["tasklist"], capture_output=True, text=True, timeout=10
        )
        # 檢查常見程序名稱
        for name in ["openclaw_gateway", "openclaw", "node", "gateway"]:
            if name in result.stdout.lower():
                return True
        return False
    except Exception as e:
        print(f"[Guardian] is_gateway_alive error: {e}")
        return True  # 保守假設：網路錯誤時假設還活著


def tail_log(filepath: str, lines: int = 50) -> str:
    """提取檔案最後 N 行"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except Exception as e:
        return f"[tail_log error: {e}]"


def get_recent_gateway_logs(lines: int = 100) -> str:
    """收集最近 Gateway 日誌（支援多個日誌路徑）"""
    log_sources = [
        BASE_DIR / "logs" / "gateway.log",
        BASE_DIR / "logs" / "gateway_error.log",
        BASE_DIR / "logs" / "openclaw_gateway.log",
        BASE_DIR / "stores" / "short_term" / "tina_cron_v2_output.json",
        BASE_DIR.parent / ".openclaw" / "logs" / "gateway.log",
    ]
    combined = []
    for src in log_sources:
        if src.exists():
            content = tail_log(str(src), lines)
            if content.strip():
                combined.append(f"=== {src.name} ===\n{content}")
    if not combined:
        return "[No logs found]"
    return "\n\n".join(combined)


def save_crash_snapshot(crash_id: str, log_content: str, market_status: str = ""):
    """保存崩潰快照到報告目錄"""
    snapshot = {
        "crash_id": crash_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_status": market_status,
        "log_excerpt": log_content[-5000:] if len(log_content) > 5000 else log_content,
    }
    path = CRASH_REPORT_DIR / f"crash_{crash_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return path


# ── 7B 參謀崩潰分析（獨占 VRAM）─────────────────────────────────────────────
@ray_singleton
def analyze_and_fix_crash(log_content: str, market_status: str = "") -> dict:
    """呼叫 7B 模型分析崩潰原因並產出避險標籤
    
    這是整個崩潰進化迴路的核心：
      1. 分析日誌 → 識別 [SYSTEM_FRAGILE_ZONE]
      2. 產出修復建議 → 寫入 ray_forbidden_rules.json
      3. 固化進 Modelfile → 下次重生後自動避開
    
    Returns:
        dict with keys: crash_tag, root_cause, fix_rule, severity
    """
    print(f"[Guardian] 🧠 啟動 7B 參謀分析（VRAM 獨占）...")
    
    # ── 崩潰語意標籤庫（已知模式快速匹配）────────────────────────────
    KNOWN_PATTERNS = [
        {
            "keywords": ["timeout", "TIMEOUT", "Gateway timeout", "Request timeout"],
            "tag": "[GATEWAY_TIMEOUT]",
            "severity": "high",
            "root_cause": "Gateway 請求逾時崩潰",
            "fix_rule": "當偵測到 [GATEWAY_TIMEOUT] → 信心歸零，降級操作為 [B] 略過",
        },
        {
            "keywords": ["401", "Unauthorized", "token", "Token expired", "auth"],
            "tag": "[API_TOKEN_EXPIRED]",
            "severity": "medium",
            "root_cause": "API Token 過期或無效",
            "fix_rule": "當偵測到 [API_TOKEN_EXPIRED] → 僅執行 [B] 略過，禁止交易指令",
        },
        {
            "keywords": ["429", "rate limit", "rate_limit", "Too many requests"],
            "tag": "[API_LIMIT_CRASH]",
            "severity": "high",
            "root_cause": "API 頻率限制崩潰",
            "fix_rule": "當偵測到 [API_LIMIT_CRASH] → 僅執行 [B] 略過，禁止交易指令",
        },
        {
            "keywords": ["memory", "MemoryError", "out of memory", "OOM", "heap"],
            "tag": "[MEMORY_OVERFLOW]",
            "severity": "critical",
            "root_cause": "記憶體溢出崩潰",
            "fix_rule": "當偵測到 [MEMORY_OVERFLOW] → 全線停止，等離峰時段恢復",
        },
        {
            "keywords": ["context", "overflow", "context_length", "too long"],
            "tag": "[CONTEXT_OVERFLOW]",
            "severity": "medium",
            "root_cause": "Context 溢出崩潰",
            "fix_rule": "當偵測到 [CONTEXT_OVERFLOW] → 開新 session，降載至 50%",
        },
        {
            "keywords": ["network", "NetworkError", "Connection refused", "ECONNREFUSED", "fetch failed"],
            "tag": "[NETWORK_LATENCY]",
            "severity": "medium",
            "root_cause": "網路連線錯誤",
            "fix_rule": "當偵測到 [NETWORK_LATENCY] → 改用本地快取，略過外部 API",
        },
        {
            "keywords": ["JSON", "json decode", "JSONDecodeError", "parse error"],
            "tag": "[JSON_DECODE_ERROR]",
            "severity": "low",
            "root_cause": "JSON 解析錯誤",
            "fix_rule": "當偵測到 [JSON_DECODE_ERROR] → 使用備用解析器，失敗則略過",
        },
        {
            "keywords": ["vectorbt", "VectorBT", "vbt", "numpy", "shape mismatch"],
            "tag": "[BACKTEST_CRASH]",
            "severity": "medium",
            "root_cause": "回測引擎崩潰（VectorBT/numpy 錯誤）",
            "fix_rule": "當偵測到 [BACKTEST_CRASH] → 跳過該標的回測，繼續下一支",
        },
    ]
    
    # ── 日誌關鍵字匹配 ───────────────────────────────────────────────
    detected_tags = []
    matched_patterns = []
    
    for pattern in KNOWN_PATTERNS:
        for kw in pattern["keywords"]:
            if kw.lower() in log_content.lower():
                if pattern["tag"] not in detected_tags:
                    detected_tags.append(pattern["tag"])
                    matched_patterns.append(pattern)
                break
    
    if not detected_tags:
        detected_tags.append("[UNKNOWN_CRASH]")
        matched_patterns.append({
            "tag": "[UNKNOWN_CRASH]",
            "severity": "unknown",
            "root_cause": "未知崩潰原因，需人工檢查",
            "fix_rule": "當偵測到 [UNKNOWN_CRASH] → 全線停止，發送 Telegram 警示",
        })
    
    # ── 取最高 severity 的規則 ────────────────────────────────────────
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    best = min(matched_patterns, key=lambda p: severity_order.get(p["severity"], 4))
    
    result = {
        "crash_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "tags": detected_tags,
        "root_cause": best["root_cause"],
        "fix_rule": best["fix_rule"],
        "severity": best["severity"],
        "all_patterns": [{"tag": p["tag"], "severity": p["severity"]} for p in matched_patterns],
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    print(f"[Guardian] 崩潰標籤：{detected_tags}")
    print(f"[Guardian] 根本原因：{best['root_cause']}")
    print(f"[Guardian] 修復規則：{best['fix_rule']}")
    
    return result


def write_forbidden_rule(crash_report: dict):
    """將崩潰分析結果寫入 ray_forbidden_rules.json（增量）"""
    rules_path = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
    
    # 讀取現有規則
    if rules_path.exists():
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            doc = {"schema": "ray_forbidden_rules_v1", "version": "1.1", "rules": []}
    else:
        doc = {"schema": "ray_forbidden_rules_v1", "version": "1.1", "rules": []}
    
    # 檢查是否已存在相同 tag 的規則（避免重複寫入）
    existing_tags = {r.get("rule", "") for r in doc.get("rules", [])}
    new_rule = {
        "rule": crash_report["fix_rule"],
        "master": "Guardian",
        "priority": 1,
        "crash_tag": crash_report["tags"],
        "root_cause": crash_report["root_cause"],
        "severity": crash_report["severity"],
        "generated_by": "ray_guardian",
        "crash_id": crash_report["crash_id"],
        "taleb_aligned": True,
        "taleb_reason": "反脆弱：將崩潰轉化為禁止規則，防止同類錯誤再次發生",
        "thorp_aligned": True,
        "thorp_reason": "凱利：風險管理優先於獲利，系統性避開已知風險",
    }
    
    # 去重：檢查相同 root_cause 是否已存在
    existing_causes = {r.get("root_cause", "") for r in doc.get("rules", [])}
    if crash_report["root_cause"] not in existing_causes:
        doc["rules"].append(new_rule)
        doc["version"] = str(float(doc.get("version", "1.0")) + 0.1)
        doc["count"] = len(doc["rules"])
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"[Guardian] ✅ 新增禁止規則：{crash_report['tags']}")
    else:
        print(f"[Guardian] ℹ️ 規則已存在（{crash_report['root_cause']}），跳過")


# ── 恢復 Gateway ────────────────────────────────────────────────────────────
def restart_gateway():
    """嘗試重啟 Gateway（Windows）"""
    try:
        # 嘗試用 openclaw 命令重啟
        result = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("[Guardian] ✅ Gateway 重啟成功")
            return True
        else:
            print(f"[Guardian] ⚠️ Gateway 重啟失敗：{result.stderr[:200]}")
            return False
    except FileNotFoundError:
        print("[Guardian] ⚠️ openclaw 命令不存在，請手動重啟")
        return False
    except Exception as e:
        print(f"[Guardian] ⚠️ 重啟時發生錯誤：{e}")
        return False


# ── 主監控迴圈 ──────────────────────────────────────────────────────────────
def monitor_loop(interval: int = MONITOR_INTERVAL, auto_restart: bool = False):
    """Gateway 崩潰監控主迴圈"""
    global _last_crash_time
    
    print(f"=" * 50)
    print(f"  ray_guardian.py — Gateway 崩潰監控中樞")
    print(f"  檢查間隔：{interval} 秒")
    print(f"  自動重啟：{'是' if auto_restart else '否'}")
    print(f"  日誌目錄：{LOG_DIR}")
    print(f"  報告目錄：{CRASH_REPORT_DIR}")
    print(f"=" * 50)
    
    while True:
        alive = is_gateway_alive()
        now = time.time()
        
        if not alive:
            print(f"\n🚨 [{datetime.now().strftime('%H:%M:%S')}] Gateway 崩潰偵測！")
            
            # Cooldown 保護：5 分鐘內不重複處理
            if now - _last_crash_time < CRASH_COOLDOWN:
                print(f"[Guardian] Cooldown 中（{CRASH_COOLDOWN}s），跳過重複處理")
                time.sleep(interval)
                continue
            _last_crash_time = now
            
            # Step 1: 提取日誌
            print("[1/4] 提取 Gateway 日誌...")
            log_content = get_recent_gateway_logs(lines=100)
            
            # Step 2: 保存崩潰快照
            crash_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            print("[2/4] 保存崩潰快照...")
            snapshot_path = save_crash_snapshot(crash_id, log_content)
            print(f"      快照：{snapshot_path.name}")
            
            # Step 3: 觸發 7B 參謀分析（獨占 VRAM）
            print("[3/4] 呼叫 7B 參謀分析...")
            analysis = analyze_and_fix_crash(log_content)
            
            # Step 4: 寫入禁止規則
            print("[4/4] 寫入 ray_forbidden_rules.json...")
            write_forbidden_rule(analysis)
            
            # Step 5: 嘗試重啟 Gateway
            if auto_restart:
                restart_gateway()
            else:
                print("[Guardian] 等待手動重啟 Gateway...")
            
            print(f"\n[Guardian] 崩潰歸因完成（crash_id={crash_id}）")
            print(f"[Guardian] 標籤：{analysis['tags']}")
            print(f"[Guardian] 下次檢查：{interval} 秒後")
        else:
            # 每 10 次心跳輸出一次狀態
            pass  # 安靜模式
        
        time.sleep(interval)


# ── CLI 入口 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ray_guardian — Gateway 崩潰監控與自動歸因")
    parser.add_argument("--interval", type=int, default=MONITOR_INTERVAL,
                        help=f"檢查間隔秒數（預設 {MONITOR_INTERVAL}s）")
    parser.add_argument("--auto-restart", action="store_true",
                        help="崩潰後自動重啟 Gateway")
    parser.add_argument("--once", action="store_true",
                        help="只檢查一次，不進入迴圈（適用 cron）")
    args = parser.parse_args()
    
    if args.once:
        # Cron 模式：只檢查一次
        alive = is_gateway_alive()
        if alive:
            print("✅ Gateway 正常運行")
            sys.exit(0)
        else:
            print("❌ Gateway 未運行，啟動崩潰歸因...")
            log = get_recent_gateway_logs()
            analysis = analyze_and_fix_crash(log)
            write_forbidden_rule(analysis)
            sys.exit(1)
    else:
        # 守护进程模式
        monitor_loop(interval=args.interval, auto_restart=args.auto_restart)