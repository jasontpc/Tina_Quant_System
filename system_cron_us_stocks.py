"""
US Stock Daily Report Cron Setup
Schedules: Mon-Fri 08:30 EST (before US market opens)
"""

import subprocess
import sys
import os

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "us_stock_monitor.py")

# OpenClaw cron: minute hour day month weekday
# 08:30 EST = 13:30 UTC = 30 13 * * 1-5
# We need to register this with OpenClaw's cron system

def setup_cron():
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list"],
            capture_output=True, text=True
        )
        print("Current crons:")
        print(result.stdout)
    except FileNotFoundError:
        print("openclaw CLI not found, trying direct approach")

    # The cron will be set up via the automation-scheduler skill
    # For now, we document the schedule here
    schedule = "30 13 * * 1-5"  # UTC = 08:30 EST
    print(f"\nRecommended cron schedule for US Stock Monitor:")
    print(f"Schedule: {schedule} (08:30 EST Mon-Fri)")
    print(f"Script: {SCRIPT_PATH}")
    print(f"Command: python {SCRIPT_PATH}")
    print("\nTo add via automation-scheduler skill, use:")
    print(f"  openclaw cron add --name 'us_stock_daily' \\")
    print(f"    --schedule '{schedule}' \\")
    print(f"    --command 'python {SCRIPT_PATH}' \\")
    print(f"    --channel telegram")

if __name__ == "__main__":
    setup_cron()