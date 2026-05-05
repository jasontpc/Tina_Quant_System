# -*- coding: utf-8 -*-
"""
Unused Scripts Finder - Tina Quant System
Scans scripts/, backtest/, automation/ directories for scripts not recently used.
Outputs: reports/unused_scripts_report_{date}.md + data/unused_scripts_report.json
"""
import os
import json
from datetime import datetime, timedelta

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
NOW = datetime.now()
CUTOFF_DAYS = 14  # 14+ days = unused

# Active scripts referenced by cron/automation
ACTIVE_SCRIPTS = {
    "automation_loop.py", "cron_analyzer.py", "cron_optimizer.py",
    "system_health_check.py", "system_idle_checker.py", "trade_failure_analyzer.py",
    "winrate_optimizer.py", "full_backtest_optimizer.py", "update_progress.py",
    "nana_hourly_check.py", "nana_hourly_report.py", "data_audit.py",
    "daily_premarket.py", "midday.py", "closing.py", "global_market.py",
    "keep_alive.py", "openclaw_monitor.py", "gateway_monitor.py",
}

def scan_dir(dir_path, dirs_to_scan):
    results = []
    for d in dirs_to_scan:
        full = os.path.join(dir_path, d)
        if not os.path.isdir(full):
            continue
        for f in os.listdir(full):
            if not f.endswith(".py"):
                continue
            fp = os.path.join(full, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
            age_days = (NOW - mtime).days
            results.append({
                "path": fp.replace(BASE, "").lstrip("\\"),
                "file": f,
                "dir": d,
                "last_modified": mtime.strftime("%Y-%m-%d %H:%M"),
                "age_days": age_days,
                "unused": age_days >= CUTOFF_DAYS
            })
    return results

def assess_duplicates(all_scripts):
    """Assess which scripts are superseded by others"""
    # Known superseded patterns
    superseded = {
        "analyze_2330.py": "core/tina_system.py",
        "analyze_2454.py": "core/tina_system.py",
        "analyze_dbs.py": "scripts/db_check_suite.py",
        "check_db.py": "scripts/db_health_check.py",
        "check_db_full.py": "scripts/db_check_suite.py",
        "check_db_schema.py": "scripts/db_status.py",
        "check_db_schema2.py": "scripts/db_status.py",
        "db_status2.py": "scripts/db_status.py",
        "db_status_full.py": "scripts/db_status.py",
        "check_main_dbs.py": "scripts/db_health_check.py",
        "check_screener_db.py": "scripts/db_status.py",
        "check_sherry_db.py": "scripts/maggy_db_updater.py",
        "check_sherry_dbs.py": "scripts/maggy_db_updater.py",
        "check_etf_db.py": "scripts/tw_active_etf_tracker.py",
        "check_us_db.py": "scripts/us_value_growth_screener.py",
        "check_us_db2.py": "scripts/us_value_growth_screener.py",
        "debug_check.py": "scripts/db_check_suite.py",
        "debug_check2.py": "scripts/db_check_suite.py",
        "debug_vogel.py": "scripts/yuan_zheng2_tracker.py",
        "check_vogel.py": "scripts/yuan_zheng2_tracker.py",
        "check_tx.py": "scripts/ray_db_updater.py",
        "check_tx2.py": "scripts/ray_db_updater.py",
        "check_tx3.py": "scripts/ray_db_updater.py",
        "quick_db_check.py": "scripts/db_health_check.py",
        "temp_check_db.py": "scripts/db_status.py",
        "test_db.py": "scripts/quick_check_suite.py",
        "test_db_check.py": "scripts/quick_check_suite.py",
        "debug_symbols.py": "scripts/twse_symbol_validator.py",
        "fix_chinese_names.py": "scripts/update_stock_names.py",
        "fix_nana.py": "teams/nana/nana_improved.py",
        "check_cols.py": "scripts/db_analysis.py",
        "check_data_coverage.py": "scripts/db_analysis.py",
        "check_data_freshness.py": "scripts/stale_data_alert.py",
        "check_coverage.py": "scripts/db_analysis.py",
        "check_inst_coverage.py": "scripts/institutional_flow_analyzer.py",
        "check_institutional.py": "scripts/institutional_flow_analyzer.py",
        "rsi_audit.py": "scripts/nana_db_updater.py",
        "debug_rsi.py": "scripts/nana_db_updater.py",
        "verify_latest_data.py": "scripts/stale_data_alert.py",
        "verify_trends_db.py": "scripts/trending_report.py",
    }
    for s in all_scripts:
        key = os.path.basename(s["path"])
        if key in superseded:
            s["superseded_by"] = superseded[key]
            s["recommendation"] = "delete"
        elif s["unused"]:
            s["recommendation"] = "review"
        else:
            s["recommendation"] = "keep"
    return all_scripts

def main():
    print("[Unused Scripts Finder] Starting scan...")

    dirs = ["scripts", "backtest", "automation"]
    all_items = scan_dir(BASE, dirs)

    # Mark active
    for item in all_items:
        if item["file"] in ACTIVE_SCRIPTS:
            item["in_cron"] = True
        else:
            item["in_cron"] = False

    assess_duplicates(all_items)

    unused = [x for x in all_items if x["unused"]]
    recent = [x for x in all_items if not x["unused"]]

    print(f"Total scanned: {len(all_items)}")
    print(f"  Unused (14+ days): {len(unused)}")
    print(f"  Recent: {len(recent)}")

    # JSON report
    report_json = {
        "generated_at": NOW.strftime("%Y-%m-%d %H:%M:%S"),
        "cutoff_days": CUTOFF_DAYS,
        "total_scanned": len(all_items),
        "unused_count": len(unused),
        "recent_count": len(recent),
        "unused_scripts": sorted(unused, key=lambda x: x["age_days"], reverse=True),
        "recent_scripts": sorted(recent, key=lambda x: x["age_days"], reverse=True)[:20],
    }

    json_path = os.path.join(BASE, "data", "unused_scripts_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)
    print(f"JSON report: {json_path}")

    # Markdown report
    md_path = os.path.join(BASE, "reports", f"unused_scripts_report_{NOW.strftime('%Y%m%d')}.md")
    lines = [
        f"# Unused Scripts Report - {NOW.strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## Summary",
        f"- Total scanned: {len(all_items)}",
        f"- Unused (14+ days): {len(unused)}",
        f"- Recent: {len(recent)}",
        f"",
        f"## Unused Scripts ({len(unused)} files)",
        f"",
    ]

    if unused:
        for s in sorted(unused, key=lambda x: x["age_days"], reverse=True):
            rec = s.get("recommendation", "review")
            sup = f" → superseded by `{s.get('superseded_by', '?')}`" if s.get("superseded_by") else ""
            lines.append(f"- `{s['path']}` — {s['last_modified']} ({s['age_days']} days ago) [{rec}]{sup}")
    else:
        lines.append("_No unused scripts found._")

    lines.extend([
        f"",
        f"## Recent Scripts (sample)",
        f"",
    ])
    for s in sorted(recent, key=lambda x: x["age_days"], reverse=True)[:15]:
        lines.append(f"- `{s['path']}` — {s['last_modified']} ({s['age_days']} days ago)")

    lines.extend([
        f"",
        f"## Recommendations",
        f"",
        f"### Delete (superseded by active scripts)",
    ])
    delete_candidates = [s for s in unused if s.get("recommendation") == "delete"]
    if delete_candidates:
        for s in delete_candidates:
            lines.append(f"- `{s['path']}` (→ `{s.get('superseded_by', '')}`)")
    else:
        lines.append("_None identified._")

    lines.extend([
        f"",
        f"### Review (unused, no replacement)",
    ])
    review_candidates = [s for s in unused if s.get("recommendation") == "review"]
    if review_candidates:
        for s in review_candidates[:20]:
            lines.append(f"- `{s['path']}` ({s['age_days']} days old)")
    else:
        lines.append("_None._")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown report: {md_path}")
    print("[Unused Scripts Finder] Done.")

if __name__ == "__main__":
    main()