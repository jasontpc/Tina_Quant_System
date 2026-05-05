"""
Macro System Runner
執行所有宏觀法人資料抓取、更新、分析、產出報告
"""
import sys, io, os

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Set up paths - script is in scripts/, project root is parent
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # parent of scripts/
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
from scripts.macro_institutional_fetcher import fetch_all as fetch_inst
from scripts.macro_indicators_tracker import fetch_all_macro
from scripts.macro_daily_report import generate_daily_report
from scripts.institutional_flow_analyzer import analyze_flow

def run_daily_cycle(date_str=None):
    """執行每日宏觀循環"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n=== Macro Daily Cycle {date_str} ===")

    # 1. 台股法人
    print("\n[1/4] Fetching institutional data...")
    result = fetch_inst(date_str)
    print(f"  Institutional: {result['inst']} stocks, Sectors: {result['sectors']}")
    print(f"  US fund flow: {result['us_flow']} symbols")
    if result['errors']:
        print(f"  Errors: {result['errors']}")

    # 2. 宏觀指標
    print("\n[2/4] Fetching macro indicators...")
    macro = fetch_all_macro()
    for k, v in macro.items():
        if v is not None:
            print(f"  {k}: {v}")

    # 3. 分析
    print("\n[3/4] Analyzing flow...")
    analysis = analyze_flow(date_str)
    print(f"  Sentiment: {analysis['sentiment']}")
    total_net = analysis['summary']['total_net']
    print(f"  Total net: {round(total_net/1e9, 2)}B shares")

    # 4. 報告
    print("\n[4/4] Generating report...")
    report, path = generate_daily_report(date_str)
    print(f"  Saved: {path}")
    print("\n=== Complete ===")
    return report, path

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    run_daily_cycle(date_arg)
