# -*- coding: utf-8 -*-
"""
log_review.py — PowerShell 日誌檢討自動化腳本
==============================================
每日 Morning/Evening 自動檢討，識別問題、寫入記憶、產生改善建議。

用法：
  python log_review.py --mode morning          # 輕量晨間檢討
  python log_review.py --mode evening          # 完整收盤檢討
  python log_review.py --mode full --days 7     # 深度分析（過去7天）
  python log_review.py --check-disk             # 磁碟空間檢查
  python log_review.py --dry-run                # 預覽不實際寫入
"""

import sys, os, json, re, argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# ===== 路徑設定 =====
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR = BASE_DIR / "scripts"
STORES_DIR = BASE_DIR / "stores"
MEMORY_CLI = SCRIPTS_DIR / "brain_memory_cli.py"
TINA_LOG = LOGS_DIR / "tina_ps.log"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ===== 日誌寫入 =====
def write_ps_log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] [log_review] {msg}"
    try:
        with open(TINA_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass
    print(line)

def write_memory(mtype, summary, detail, source, tags, importance=5, expiry=30):
    """寫入記憶系統"""
    tags_str = ",".join(tags)
    cmd = f'python "{MEMORY_CLI}" write --type {mtype} --summary "{summary}" --detail "{detail}" --source {source} --tags "{tags_str}" --importance {importance} --expiry {expiry}'
    os.system(cmd)

def complete_job(job_name, universe, summary, metrics=""):
    """Job 完成寫入"""
    cmd = f'python "{MEMORY_CLI}" complete --job {job_name} --universe {universe}'
    if summary:
        cmd += f' --summary "{summary}"'
    if metrics:
        cmd += f' --metrics "{metrics}"'
    os.system(cmd)

# ===== 日誌分析 =====

def get_log_stats(days=1):
    """統計所有 .log 檔案的 ERROR/WARNING/INFO"""
    stats = {}
    SKIP_FILES = {"errors.log", "tina_ps.log"}

    for lf in LOGS_DIR.glob("*.log"):
        if lf.name in SKIP_FILES:
            continue
        try:
            text = lf.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            errors = warnings = infos = 0

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                # 精確匹配 level：[ERROR] [WARNING] [INFO] 或行首 ERROR/WARNING
                has_error = '[ERROR]' in line_stripped or re.search(r'\bERROR\b', line_stripped) is not None
                has_warning = '[WARNING]' in line_stripped or '[WARN]' in line_stripped or re.search(r'\bWARNING\b', line_stripped) is not None
                has_info = '[INFO]' in line_stripped or re.search(r'\bINFO\b', line_stripped) is not None

                if has_error:
                    errors += 1
                elif has_warning:
                    warnings += 1
                elif has_info:
                    infos += 1

            size_kb = lf.stat().st_size / 1024
            stats[lf.name] = {
                "size_kb": round(size_kb, 1),
                "total_lines": len(lines),
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
                "recent": lines[-5:] if lines else []
            }
        except Exception as e:
            stats[lf.name] = {"error": str(e)}

    return stats

def analyze_errors(days=1):
    """分析 errors.log 中的錯誤"""
    errors_file = LOGS_DIR / "errors.log"
    if not errors_file.exists():
        return [], 0

    cutoff = datetime.now() - timedelta(days=days)
    error_lines = []

    try:
        lines = errors_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if m:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                if ts >= cutoff:
                    error_lines.append(line.strip())
    except:
        pass

    return error_lines, len(error_lines)

def detect_anomalies(stats, errors):
    """偵測異常模式"""
    anomalies = []

    # 1. 高錯誤率
    for name, s in stats.items():
        if "error" in s:
            continue
        total = s["errors"] + s["warnings"] + s["infos"]
        if total > 0:
            error_rate = s["errors"] / total
            if error_rate > 0.3:
                anomalies.append(f"HIGH_ERROR_RATE: {name} ({error_rate:.0%})")
            if s["errors"] > 10:
                anomalies.append(f"MANY_ERRORS: {name} ({s['errors']} errors)")

    # 2. 檔案過大（無輪轉）
    for name, s in stats.items():
        if s.get("size_kb", 0) > 500:
            anomalies.append(f"LARGE_FILE: {name} ({s['size_kb']} KB)")

    # 3. 磁碟空間
    try:
        import shutil
        usage = shutil.disk_usage("C:\\")
        free_gb = usage.free / (1024**3)
        if free_gb < 20:
            anomalies.append(f"LOW_DISK: {free_gb:.1f} GB free")
    except:
        pass

    # 4. 特定錯誤模式
    error_text = " ".join(errors)
    if "FinMind" in error_text or "400" in error_text:
        anomalies.append("FinMind_API_ERRORS: FinMind Token 可能需要更新")
    if "TWSE T86" in error_text:
        anomalies.append("TWSE_T86_ERRORS: 證交所資料抓取異常")
    if "margin" in error_text.lower():
        anomalies.append("MARGIN_DATA_ERRORS: 融資融券資料缺口")

    return anomalies

def extract_lesson(anomalies):
    """從異常中提煉 Lesson"""
    lessons = []

    if any("FinMind" in a for a in anomalies):
        lessons.append({
            "summary": "FinMind API 持續返回 400 錯誤",
            "detail": "可能是 Token 過期或 API 端點變更，需要更新 TOOLS.md 中的 FinMind Token",
            "tags": ["api_error", "finmind", "maintenance"],
            "importance": 8
        })

    if any("TWSE" in a for a in anomalies):
        lessons.append({
            "summary": "TWSE T86 法人資料出現编碼錯誤",
            "detail": "Big5 解析問題，可能是證交所回應格式變更或非標準字符",
            "tags": ["encoding", "twse", "data_quality"],
            "importance": 7
        })

    if any("LOW_DISK" in a for a in anomalies):
        lessons.append({
            "summary": "磁碟空間低於 20GB",
            "detail": "建議執行 log_rotation.py 或手動清理舊日誌",
            "tags": ["system", "disk_space", "maintenance"],
            "importance": 9
        })

    return lessons

# ===== 報告生成 =====

def generate_report(mode, stats, errors, anomalies, lessons):
    """產出檢討報告"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    if mode == "morning":
        lines.append(f"=== Morning Log Review | {ts} ===")
        lines.append(f"Logs analyzed: {len(stats)}")
        total_errors = sum(s.get("errors", 0) for s in stats.values() if "error" not in s)
        total_warnings = sum(s.get("warnings", 0) for s in stats.values() if "error" not in s)
        lines.append(f"Total: {total_errors} errors, {total_warnings} warnings")

        if anomalies:
            lines.append(f"\n⚠️ Anomalies ({len(anomalies)}):")
            for a in anomalies[:5]:
                lines.append(f"  - {a}")
        else:
            lines.append("\n✅ No anomalies detected")

    elif mode == "evening":
        lines.append(f"=== Evening Log Review | {ts} ===")
        lines.append(f"\n📊 Log Statistics:")
        for name, s in sorted(stats.items(), key=lambda x: x[1].get("errors", 0), reverse=True):
            if "error" in s:
                continue
            e = s.get("errors", 0)
            w = s.get("warnings", 0)
            lines.append(f"  {name:<35} E={e:>3} W={w:>3} ({s.get('size_kb', 0):.0f}KB)")

        if errors:
            lines.append(f"\n🔴 Recent Errors ({len(errors)}):")
            for e in errors[-10:]:
                lines.append(f"  {e[:90]}")

        if anomalies:
            lines.append(f"\n⚠️ Anomalies:")
            for a in anomalies:
                lines.append(f"  - {a}")

        if lessons:
            lines.append(f"\n📝 Lessons for today:")
            for l in lessons:
                lines.append(f"  • {l['summary']}")

    elif mode == "full":
        lines.append(f"=== Full Log Review (Deep) | {ts} ===")
        lines.append(f"\n📈 System Health:")
        for name, s in sorted(stats.items(), key=lambda x: x[1].get("size_kb", 0), reverse=True):
            if "error" in s:
                continue
            lines.append(f"  {name}: {s.get('errors', 0)}E / {s.get('warnings', 0)}W / {s.get('size_kb', 0):.0f}KB")

        lines.append(f"\n🔴 Error Pattern Analysis ({len(errors)} errors):")
        error_groups = defaultdict(int)
        for e in errors:
            if "FinMind" in e:
                error_groups["FinMind API"] += 1
            elif "TWSE" in e:
                error_groups["TWSE"] += 1
            elif "margin" in e.lower():
                error_groups["Margin Data"] += 1
            else:
                error_groups["Other"] += 1

        for group, count in sorted(error_groups.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {group}: {count} occurrences")

        if anomalies:
            lines.append(f"\n⚠️ Anomalies ({len(anomalies)}):")
            for a in anomalies:
                lines.append(f"  - {a}")

        if lessons:
            lines.append(f"\n📝 Lessons Learned ({len(lessons)}):")
            for l in lessons:
                lines.append(f"  • [{l['importance']}] {l['summary']}")
                lines.append(f"    Detail: {l['detail']}")

        lines.append("\n📋 Recommendations:")
        if any("LARGE_FILE" in a for a in anomalies):
            lines.append("  1. 執行 log_rotation.py --dry-run 查看需要清理的檔案")
        if any("FinMind" in a for a in anomalies):
            lines.append("  2. 更新 TOOLS.md 中的 FinMind Token")
        if any("TWSE" in a for a in anomalies):
            lines.append("  3. 檢查 macro_institutional_fetcher.py 的 Big5 解析")
        if any("LOW_DISK" in a for a in anomalies):
            lines.append("  4. 緊急：清理 logs/ 目錄或刪除舊備份檔案")

    return "\n".join(lines)

# ===== 主流程 =====

def run_review(mode, days, dry_run):
    write_ps_log(f"Starting {mode} review (days={days})")

    # 1. 讀取統計
    stats = get_log_stats(days=days)
    errors, error_count = analyze_errors(days=days)

    # 2. 偵測異常
    anomalies = detect_anomalies(stats, errors)
    lessons = extract_lesson(anomalies) if mode in ("evening", "full") else []

    # 3. 產出報告
    report = generate_report(mode, stats, errors, anomalies, lessons)
    print("\n" + report + "\n")

    if dry_run:
        write_ps_log("[DRY RUN] Skipping memory writes")
        return

    # 4. 寫入記憶
    if mode in ("evening", "full"):
        obs_summary = f"Log review ({mode}): {len(stats)} logs, {error_count} errors, {len(anomalies)} anomalies"
        obs_detail = "\n".join(anomalies[:5]) if anomalies else "No anomalies"
        write_memory("observation", obs_summary, obs_detail, "log_review",
                    ["log_review", mode, "system"], importance=6, expiry=30)

        for l in lessons:
            write_memory("lesson", l["summary"], l["detail"], "log_review",
                        l["tags"], importance=l["importance"], expiry=90)

        metrics = {
            "logs_analyzed": len(stats),
            "errors": error_count,
            "anomalies": len(anomalies),
            "lessons": len(lessons),
            "timestamp": datetime.now().isoformat()
        }

        complete_job(f"log_review_{mode}", "MULTI", f"Log review {mode}: {len(anomalies)} anomalies", json.dumps(metrics))

    write_ps_log(f"Review complete: {error_count} errors, {len(anomalies)} anomalies, {len(lessons)} lessons")

# ===== CLI =====

def main():
    parser = argparse.ArgumentParser(description="Tina Log Review Automation")
    parser.add_argument("--mode", "-m", choices=["morning", "evening", "full"], default="morning",
                        help="morning (light), evening (standard), full (deep)")
    parser.add_argument("--days", "-d", type=int, default=1, help="Days to analyze")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--check-disk", action="store_true", help="Disk space check only")

    args = parser.parse_args()

    if args.check_disk:
        try:
            import shutil
            usage = shutil.disk_usage("C:\\")
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            pct = (usage.free / usage.total) * 100
            print(f"Disk: {free_gb:.1f}GB free / {total_gb:.1f}GB total ({pct:.1f}% used)")
            if free_gb < 20:
                print("⚠️ LOW DISK WARNING: < 20GB free")
            else:
                print("✅ Disk space OK")
            return
        except Exception as e:
            print(f"Error: {e}")
            return

    run_review(args.mode, args.days, args.dry_run)

if __name__ == "__main__":
    main()