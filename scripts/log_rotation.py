# -*- coding: utf-8 -*-
"""
log_rotation.py — Tina Log Rotation & Error Isolation
功能：
1. 從所有 .log 檔案抽出 ERROR/WARNING 寫入 logs/errors.log
2. 清理 7 天以上的舊日誌
3. 統一日誌格式（移除乱码）

使用方法：
  python scripts/log_rotation.py        # 每日執行
  python scripts/log_rotation.py --dry-run  # 預覽不實際執行
"""
import sys, os, re, argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ===== Config =====
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOGS_DIR = BASE_DIR / "logs"
ERRORS_LOG = LOGS_DIR / "errors.log"
DAYS_TO_KEEP = 7

# ===== Deduplicate =====
existing_errors = set()
if ERRORS_LOG.exists():
    with open(ERRORS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            existing_errors.add(line.strip()[:120])

new_errors = []

# ===== Extract Errors =====
def extract_errors(log_path):
    """從單一 .log 檔案抽出 ERROR/WARNING 行"""
    if not log_path.exists():
        return

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 統一時間戳
                ts_match = re.match(
                    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,\.]\d{3}|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\])",
                    line
                )
                ts = ts_match.group(1) if ts_match else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rest = line[len(ts_match.group(0)):].strip() if ts_match else line

                # 判斷級別
                level = "UNKNOWN"
                for kw in ["[ERROR]", " ERROR ", "ERROR:", " ERROR -"]:
                    if kw in line:
                        level = "ERROR"
                        break
                if level == "UNKNOWN":
                    for kw in ["[WARNING]", " WARNING ", "WARNING:", " WARN ", " WARNING -"]:
                        if kw in line:
                            level = "WARNING"
                            break

                if level == "UNKNOWN":
                    continue

                # Source
                src = log_path.stem
                src_match = re.search(r"\[([a-z_]+)\]", line)
                if src_match:
                    src = src_match.group(1)

                clean_line = f"{ts} [{level}] [{src}] {rest}"
                # 移除乱码
                clean_line = clean_line.encode("ascii", errors="replace").decode("ascii")
                if clean_line not in existing_errors:
                    new_errors.append(clean_line)

    except Exception as e:
        print(f"  Skip {log_path.name}: {e}")

# ===== Clean Old Logs =====
def clean_old_logs():
    """刪除 7 天前舊日誌"""
    cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    removed_files = []

    for f in LOGS_DIR.glob("*.log"):
        if f.name == "errors.log":
            continue
        if f.stat().st_mtime < cutoff.timestamp():
            removed_files.append(f.name)
            f.unlink()

    for f in LOGS_DIR.glob("db_audit_*.json"):
        if f.stat().st_mtime < cutoff.timestamp():
            removed_files.append(f.name)
            f.unlink()

    return removed_files

# ===== Run =====
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Tina Log Rotation ===")
    print(f"Logs dir : {LOGS_DIR}")
    print(f"Errors   : {ERRORS_LOG}")
    print(f"Keep     : {DAYS_TO_KEEP} days")

    # Step 1: Scan
    log_files = [f for f in LOGS_DIR.glob("*.log") if f.name != "errors.log"]
    print(f"Scanning : {len(log_files)} files...")

    for lf in log_files:
        size_kb = lf.stat().st_size / 1024
        print(f"  {lf.name:<40} {size_kb:>7.1f} KB")
        extract_errors(lf)

    # Step 2: Write errors
    if new_errors:
        print(f"\nNew errors : {len(new_errors)} entries")
        if not args.dry_run:
            with open(ERRORS_LOG, "a", encoding="utf-8") as f:
                for e in new_errors:
                    f.write(e + "\n")
            print("  -> errors.log updated")
        else:
            print("  -> [DRY RUN] skipped")
    else:
        print("\nNo new errors.")

    # Step 3: Cleanup
    print(f"\nCleaning logs older than {DAYS_TO_KEEP} days...")
    removed = clean_old_logs() if not args.dry_run else []
    if removed:
        for name in removed:
            print(f"  Removed: {name}")
    else:
        print("  Nothing to remove.")

    print("\n=== Done ===")

if __name__ == "__main__":
    main()