import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from datetime import datetime, timedelta
from scripts.macro_indicators_tracker import fetch_all_macro
from scripts.macro_institutional_fetcher import fetch_all as fetch_inst
from scripts.institutional_flow_analyzer import analyze_flow

def run_premarket():
    """美股開盤前（09:00）宏觀報告"""
    print("\n=== Macro Pre-Market Report ===")
    
    # Refresh macro indicators
    print("\n[1/2] Refreshing macro indicators...")
    macro = fetch_all_macro()
    for k, v in macro.items():
        if v is not None:
            print(f"  {k}: {v}")
    
    # Get last trading day's institutional data
    print("\n[2/2] Last institutional data...")
    today = datetime.now()
    for i in range(5):
        d = today - timedelta(days=i+1)
        d_str = d.strftime("%Y-%m-%d")
        if d.weekday() < 5:  # Weekday only
            analysis = analyze_flow(d_str)
            total = analysis['summary']['total_net']
            if total != 0:
                print(f"  Date: {d_str}")
                print(f"  Foreign: {round(total/1e9,2)}B")
                print(f"  Total: {round(total/1e9,2)}B")
                break
    
    print("\n=== Pre-Market Complete ===")

if __name__ == "__main__":
    run_premarket()
