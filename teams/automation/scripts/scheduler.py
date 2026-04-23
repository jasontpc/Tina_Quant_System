#!/usr/bin/env python3
"""
自動化排程管理工具
功能：查看、新增、移除排程任務
"""

import subprocess
import sys
import json
from datetime import datetime

def run_cmd(cmd):
    """執行命令並返回輸出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

def list_crons():
    """列出所有排程"""
    print("📅 Tina 系統排程任務")
    print("=" * 50)
    stdout, _ = run_cmd('openclaw cron list')
    if stdout:
        print(stdout)
    else:
        print("無法取得排程列表")

def add_cron(name, schedule, command):
    """新增排程任務"""
    cmd = f'openclaw cron schedule "{schedule}" "{command}"'
    print(f"➕ 新增排程：{name}")
    print(f"   時間：{schedule}")
    print(f"   命令：{command}")
    stdout, stderr = run_cmd(cmd)
    if stderr:
        print(f"❌ 錯誤：{stderr}")
    else:
        print(f"✅ 排程已新增")

def remove_cron(task_id):
    """移除排程任務"""
    cmd = f'openclaw cron remove {task_id}'
    print(f"🗑️ 移除排程：{task_id}")
    stdout, stderr = run_cmd(cmd)
    if stderr:
        print(f"❌ 錯誤：{stderr}")
    else:
        print(f"✅ 排程已移除")

def show_help():
    """顯示說明"""
    print("""
🤖 Tina 自動化排程工具

使用方法：
    python scheduler.py list              - 列出所有排程
    python scheduler.py add <名稱> <時間> <命令>  - 新增排程
    python scheduler.py remove <ID>       - 移除排程
    python scheduler.py templates         - 顯示常用範本

範例：
    python scheduler.py add "daily-report" "30 16 * * *" "python daily_report.py"
    python scheduler.py remove 1
    python scheduler.py templates
""")

def show_templates():
    """顯示常用範本"""
    templates = [
        ("每日收盤報告", "30 16 * * *", "python skills/stock-analyzer/bandwave_system/daily_report.py"),
        ("每日晚報", "0 23 * * *", "python skills/stock-analyzer/bandwave_system/daily_evening.py"),
        ("每週系統檢討", "0 10 * * 6", "python skills/stock-analyzer/bandwave_system/weekly_review.py"),
        ("股票監控檢查", "*/30 * * * *", "python skills/stock-monitor/scripts/check_alerts.py"),
    ]
    
    print("📋 Tina 系統常用排程範本")
    print("=" * 60)
    for name, schedule, cmd in templates:
        print(f"\n【{name}】")
        print(f"  時間：{schedule}")
        print(f"  命令：{cmd}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
    elif sys.argv[1] == "list":
        list_crons()
    elif sys.argv[1] == "templates":
        show_templates()
    elif sys.argv[1] == "add" and len(sys.argv) >= 5:
        name = sys.argv[2]
        schedule = sys.argv[3]
        command = " ".join(sys.argv[4:])
        add_cron(name, schedule, command)
    elif sys.argv[1] == "remove" and len(sys.argv) >= 3:
        remove_cron(sys.argv[2])
    else:
        show_help()