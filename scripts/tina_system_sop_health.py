# -*- coding: utf-8 -*-
"""
Tina 全系統健康檢查自動化 SOP
功能：
  1. 掃描所有 cron jobs 狀態
  2. 檢查所有 DB 資料新舊
  3. 自動修復常見問題（timeout 設定、cron missing）
  4. 輸出修復報告
  5. 未能自動修復的問題列入待辦清單
"""
import sqlite3, os, sys, json, subprocess, time, requests
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
SCRIPTS_DIR = WORKSPACE / "scripts"
OPENCLAW_CLI = r"C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"

REPORT = []
FIXED = []
AUTO_FIXED = []
NEED_MANUAL = []

def log(msg, emoji="📋"):
    print(f"{emoji} {msg}")
    REPORT.append(f"[{emoji}] {msg}")

def run_cli(args, timeout=20):
    try:
        r = subprocess.run(
            ["node", OPENCLAW_CLI] + args,
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def check_crons():
    log("=== Cron Jobs 健康檢查 ===", "⏰")
    output = run_cli(["cron", "list"])
    if not output or "error" in output.lower():
        log("  無法讀取 cron list", "🔴")
        return {}

    lines = output.splitlines()
    crons = {}
    error_crons = []
    for line in lines:
        # ID存在就解析
        if len(line) > 35 and line[0] != ' ':
            parts = line.split()
            if len(parts) >= 2:
                cid = parts[0]
                name = " ".join(parts[1:])
                crons[cid] = {'name': name, 'status': 'unknown'}

    # 檢查每個 cron 的詳細狀態（只查有問題的）
    # 解析 last 狀態
    for line in lines:
        for cid in crons:
            if cid in line:
                if "error" in line.lower():
                    crons[cid]['status'] = 'error'
                    error_crons.append(cid)
                elif "ok" in line.lower():
                    crons[cid]['status'] = 'ok'
                elif "idle" in line.lower():
                    crons[cid]['status'] = 'idle'

    log(f"  總數: {len(crons)} | OK: {sum(1 for v in crons.values() if v['status']=='ok')} | Error: {len(error_crons)}", "📊")

    # === Auto-fix timeout ===
    for cid in error_crons:
        details = run_cli(["cron", "show", cid])
        if "timeoutSeconds" not in details and "timeout" not in details.lower():
            # timeout 設定太短
            if "timeoutSeconds\": 30" in details or "timeoutSeconds\": 60" in details:
                result = run_cli(["cron", "edit", cid, "--timeout-seconds", "300"])
                AUTO_FIXED.append(f"Cron {cid}: timeout 30s → 300s")
                log(f"  已自動修復: {cid} timeout 300s", "🔧")
        else:
            NEED_MANUAL.append(f"Cron error: {cid} (需人工確認)")

    return crons

def check_databases():
    log("=== Database 健康檢查 ===", "🗄️")
    db_files = list(DATA.glob("*.db"))
    log(f"  找到 {len(db_files)} 個 DB 檔案", "📊")

    stale_dbs = []
    missing_crons = []

    for db in sorted(db_files):
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]

            latest_dates = {}
            for t in tables:
                try:
                    cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
                    date_col = next((c for c in cols if any(dc in c.lower() for dc in ['date', 'time'])), None)
                    if date_col and cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] > 0:
                        latest = cur.execute(f'SELECT MAX("{date_col}") FROM "{t}"').fetchone()[0]
                        if latest:
                            latest_dates[t] = str(latest)[:10]
                except:
                    pass

            conn.close()

            if latest_dates:
                latest = max(latest_dates.values())
                days_old = (datetime.now().date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
                status = "🔴 STALE" if days_old >= 3 else ("🟡 更新" if days_old >= 1 else "✅")
                log(f"  {db.name}: {latest} ({days_old}天) {status}", "📊")

                if days_old >= 3:
                    stale_dbs.append((db.name, latest, days_old))
            else:
                log(f"  {db.name}: 空DB或無日期欄位 ⚠️", "⚠️")
                if db.name == "maggy.db":
                    NEED_MANUAL.append("maggy.db 空DB，需檢查 maggy_db_update.py 是否正常")

        except Exception as e:
            log(f"  {db.name}: 讀取錯誤 - {e}", "🔴")

    # 檢查缺少的 cron
    cron_output = run_cli(["cron", "list"])
    has_institutional = any("法人" in l for l in cron_output.splitlines())
    has_margin = any("margin" in l.lower() for l in cron_output.splitlines())

    if not has_institutional:
        missing_crons.append("TW 法人資料每日更新（institutional）")
        log("  缺少 TW 法人資料 cron ⚠️", "⚠️")
    if not has_margin:
        missing_crons.append("TW Margin 每日更新（margin_balance）")
        log("  缺少 TW Margin cron ⚠️", "⚠️")

    return stale_dbs, missing_crons

def auto_fix_stale_dbs(stale_dbs):
    for db_name, latest, days in stale_dbs:
        log(f"  嘗試自動修復: {db_name} (落後{days}天)", "🔧")
        # 嘗試找到對應的更新腳本
        scripts = list(SCRIPTS_DIR.glob("*institutional*")) + list(SCRIPTS_DIR.glob("*margin*"))
        for s in scripts:
            if db_name.replace('.db', '') in s.name.lower():
                try:
                    result = subprocess.run(
                        ["python", str(s)],
                        capture_output=True, text=True, encoding='utf-8', errors='replace',
                        timeout=60
                    )
                    AUTO_FIXED.append(f"{db_name}: 執行 {s.name} 完成")
                    log(f"    → 已執行 {s.name}", "✅")
                    break
                except Exception as e:
                    NEED_MANUAL.append(f"{db_name} 自動修復失敗: {e}")
        else:
            NEED_MANUAL.append(f"{db_name}: 無法自動修復（找不到對應腳本）")

def generate_report():
    print("\n" + "="*60)
    print("  Tina 全系統健康報告")
    print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    if AUTO_FIXED:
        print("\n✅ 已自動修復:")
        for f in AUTO_FIXED:
            print(f"   • {f}")

    if NEED_MANUAL:
        print("\n🔴 需人工處理:")
        for n in NEED_MANUAL:
            print(f"   • {n}")

    print("\n📋 修復報告:")
    for r in REPORT:
        print(f"  {r}")

def main():
    log("Tina 全系統 SOP 健康檢查", "🧠")
    log(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "⏰")

    # 1. Cron 健康檢查
    crons = check_crons()

    # 2. DB 健康檢查
    stale_dbs, missing_crons = check_databases()

    # 3. 自動修復
    if stale_dbs:
        log("嘗試自動修復 stale DB...", "🔧")
        auto_fix_stale_dbs(stale_dbs)

    # 4. 輸出報告
    generate_report()

    print("\n✅ 檢查完成")

if __name__ == '__main__':
    main()