# -*- coding: utf-8 -*-
"""
Tina 全系統健康檢查腳本
功能：
  1. 檢查所有 Cron Job 狀態（jobs.json + cron list）
  2. 檢查市場現況（TWII RSI）
  3. 檢查各團隊腳本是否存在
  4. 自動嘗試修復失敗的 Cron Job
  5. 產出健檢報告
"""

import sys, os, json, subprocess, re, shutil, time
from datetime import datetime
from pathlib import Path

# ── UTF-8 設定 ──────────────────────────────────────────────
sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE   = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
TEAMS_DIR   = WORKSPACE / "teams"
REPORT_FILE = TEAMS_DIR / "tina_health_report.json"
JOBS_JSON   = Path.home() / ".openclaw" / "cron" / "jobs.json"
OPENCLAW    = Path(os.environ.get("OPENCLAW",
                   r"C:\Users\USER\AppData\Roaming\npm\openclaw.cmd"))

SCRIPT_CHECKS = {
    "nana": TEAMS_DIR / "nana" / "nana_v64.py",
    "leo":  TEAMS_DIR / "leadtrades" / "leos" / "leo_v70.py",
    "ray":  TEAMS_DIR / "ray" / "dca_market_brief.py",
}


def log(msg: str):
    print(f"  {msg}")


def print_banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print('='*60)


# ── jobs.json 讀取 ─────────────────────────────────────────
def load_jobs() -> list:
    if not JOBS_JSON.exists():
        return []
    try:
        with open(JOBS_JSON, "r", encoding="utf-8") as f:
            return json.load(f).get("jobs", [])
    except Exception:
        return []


# ── Cron 狀態：jobs.json + cron list 混合解析 ─────────────
def get_cron_status() -> dict:
    """
    jobs.json 是事實來源（不受終端編碼影響）。
    cron list 用 ID 前 8 字元定位該列，取 parts[4] 當狀態。
    """
    jobs = load_jobs()
    if not jobs:
        return {}

    # 嘗試呼叫 cron list，取即時狀態
    status_map = {}
    try:
        proc = subprocess.run(
            [str(OPENCLAW), "cron", "list"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            creationflags=0x08000000, timeout=10
        )
        raw = proc.stdout + proc.stderr
    except Exception:
        raw = ""

    # 建立 ID前綴 → 狀態 的對照（避免中文編碼問題）
    id_status = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith("ID"):
            continue
        clean = line.replace("\x00", "")
        parts = re.split(r"\s{2,}", clean)
        if len(parts) < 5:
            continue
        status = parts[4].strip().lower()
        if status in ("ok", "idle", "failed", "error", "unknown"):
            # 用 ID 前 8 字元當 key
            id8 = parts[0].strip()[:8]
            if id8:
                id_status[id8] = status

    # 組合結果
    for job in jobs:
        jid  = job["id"]
        name = job.get("name", "???")
        short_id = jid[:8]
        # 從 id_status 找即時狀態；找不到預設 idle（新job同步延遲）
        stat = id_status.get(short_id, "idle")
        status_map[jid] = {
            "name":    name,
            "status":  stat,
            "enabled": job.get("enabled", True),
        }
    return status_map


# ── 團隊腳本完整性 ────────────────────────────────────────
def check_scripts() -> dict:
    results = {}
    for key, path in SCRIPT_CHECKS.items():
        ok = path.exists()
        results[key] = ok
        log(f"{'✅' if ok else '❌'} {key}: {path.name} ({path.parent.name}/)")
    return results


# ── TWII RSI ───────────────────────────────────────────────
def get_twii_rsi() -> dict:
    try:
        import yfinance as yf
    except ImportError:
        log("⚠  yfinance 未安裝，跳過 RSI 檢查")
        return {"rsi": None, "status": "UNKNOWN"}

    try:
        hist = yf.Ticker("^TWII").history(period="3mo")
        if hist.empty or len(hist) < 30:
            return {"rsi": None, "status": "INSUFFICIENT_DATA"}
        closes = hist["Close"].dropna()
        delta  = closes.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, float("inf"))
        rsi    = round(float(100 - (100 / (1 + rs)).iloc[-1]), 1)
        status = "OVERBOUGHT" if rsi >= 70 else "OVERSOLD" if rsi <= 30 else "NEUTRAL"
        log(f"📈 TWII RSI(14): {rsi} — {status}")
        return {"rsi": rsi, "status": status}
    except Exception as e:
        log(f"⚠  TWII RSI 失敗: {e}")
        return {"rsi": None, "status": "ERROR"}


# ── 備份 jobs.json ────────────────────────────────────────
def backup_jobs() -> Path | None:
    if not JOBS_JSON.exists():
        return None
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    bck = JOBS_JSON.with_name(f"jobs_backup_{ts}.json")
    shutil.copy2(JOBS_JSON, bck)
    log(f"📦 jobs.json 備份: {bck.name}")
    return bck


# ── 重建單一失敗 Job ─────────────────────────────────────
def rebuild_job(jid: str, jname: str) -> bool:
    """新增同名 Job，確認成功後再刪除舊的。"""
    jobs = load_jobs()
    orig = next((j for j in jobs if j["id"] == jid), None)
    if not orig:
        log(f"⚠  找不到原始 Job 資料: {jname}")
        return False

    expr   = orig["schedule"]["expr"]
    sess   = orig.get("sessionTarget", "isolated")
    wake   = orig.get("wakeMode", "now")
    msg    = orig.get("payload", {}).get("message", "")
    timeout= orig.get("payload", {}).get("timeoutSeconds", 60)
    delivery = orig.get("delivery", {})
    to_ch  = delivery.get("channel", "last")
    to_dst = delivery.get("to", "telegram:1616824689")

    cmd = [
        str(OPENCLAW), "cron", "add",
        "--name", jname,
        "--cron", expr,
        "--session", sess,
        "--wake", wake,
        "--timeout-seconds", str(timeout),
        "--message", msg,
    ]
    if delivery.get("mode") == "announce":
        cmd += ["--announce"]
    if to_ch:
        cmd += ["--channel", to_ch]
    if to_dst:
        cmd += ["--to", to_dst]

    log(f"🔧 重建: {jname}")
    add = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          creationflags=0x08000000)
    if add.returncode != 0:
        log(f"  ❌ 新增失敗: {add.stderr.strip()}")
        return False

    log("  ✅ 新 Job 建立，刪除舊 Job")
    subprocess.run([str(OPENCLAW), "cron", "rm", jid],
                   capture_output=True, text=True,
                   encoding="utf-8", errors="replace",
                   creationflags=0x08000000)
    return True


# ── 主流程 ─────────────────────────────────────────────────
def run():
    print_banner("Tina 全系統健康檢查")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    log(f"時間：{ts}")

    # ── A. Cron Job ─────────────────────────────────────────
    print_banner("A. Cron Job 狀態")
    cs = get_cron_status()
    total   = len(cs)
    healthy = sum(1 for v in cs.values() if v["status"] in ("ok", "idle"))
    failed  = [jid for jid, v in cs.items() if v["status"] not in ("ok", "idle")]
    for jid, v in cs.items():
        icon = "✅" if v["status"] in ("ok", "idle") else "❌"
        log(f"  {icon} [{v['status']:8s}] {v['name']}")

    # ── B. 市場現況 ─────────────────────────────────────────
    print_banner("B. 市場現況（TWII）")
    market = get_twii_rsi()

    # ── C. 腳本完整性 ───────────────────────────────────────
    print_banner("C. 團隊腳本完整性")
    scripts_ok = check_scripts()

    # ── D. 自動修復 ─────────────────────────────────────────
    print_banner("D. 自動修復")
    actions = []
    rebuilt = []
    if failed:
        backup_jobs()
        for jid in failed:
            jname = cs[jid]["name"]
            if rebuild_job(jid, jname):
                rebuilt.append(jid)
                actions.append(f"Rebuilt: {jname}")
    else:
        log("✅ 所有 Jobs 正常，無需修復")

    # ── E. 驗證 ─────────────────────────────────────────────
    if rebuilt:
        print_banner("E. 修復後驗證")
        time.sleep(1)
        cs2 = get_cron_status()
        # 重建後 ID 改變，用名稱比對
        name_to_stat = {v["name"]: v["status"] for v in cs2.values()}
        all_ok = True
        for jid in rebuilt:
            orig_name = cs[jid]["name"]
            stat = name_to_stat.get(orig_name, "not-found")
            icon = "✅" if stat in ("ok", "idle") else "❌"
            log(f"  {icon} [{stat}] {orig_name}")
            if stat not in ("ok", "idle"):
                all_ok = False
        if all_ok:
            log("✅ 所有重建 Jobs 驗證通過")

    # ── F. 報告 ─────────────────────────────────────────────
    print_banner("F. 健檢報告")
    report = {
        "timestamp": ts,
        "market": market,
        "cron_jobs": {"total": total, "healthy": healthy, "failed": len(failed)},
        "scripts":  scripts_ok,
        "actions_taken": actions if actions else ["No action needed"],
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"📄 報告寫入: {REPORT_FILE}")

    # 終端摘要
    print(f"\n【SUMMARY】")
    print(f"  Cron Jobs : {healthy}/{total} healthy", end="" if failed else "  ✅\n")
    if failed: print(f"  ❌ {len(failed)} failed")
    print(f"  TWII RSI  : {market.get('rsi', 'N/A')} — {market.get('status', 'N/A')}")
    sn = "✅" if scripts_ok.get("nana") else "❌"
    sl = "✅" if scripts_ok.get("leo")  else "❌"
    sr = "✅" if scripts_ok.get("ray")  else "❌"
    print(f"  Scripts   : {sn} nana | {sl} leo | {sr} ray")
    print(f"  Actions   : {', '.join(actions) if actions else 'None'}")
    print()
    return report


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
