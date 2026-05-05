# -*- coding: utf-8 -*-
"""
stale_data_alert.py - Tina 量化系統過時資料警報
檢查所有 watchlist JSON 是否超過 12 小時未更新
超過 12 小時 → 發送 Telegram 警報
用法:
  python stale_data_alert.py              # 檢查並發送警報（如有需要）
  python stale_data_alert.py --check      # 僅檢查，不發送
  python stale_data_alert.py --hours 24   # 自訂過時門檻（小時）
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

WATCHLIST_FILES = {
    'nana_watchlist.json':  os.path.join(BASE, 'data', 'nana_watchlist.json'),
    'leo_watchlist.json':   os.path.join(BASE, 'data', 'leo_watchlist.json'),
    'ray_watchlist.json':   os.path.join(BASE, 'data', 'ray_watchlist.json'),
    'maggy_watchlist.json': os.path.join(BASE, 'data', 'maggy_watchlist.json'),
    'market_regime.json':   os.path.join(BASE, 'data', 'market_regime.json'),
}

def get_file_mtime(path):
    """取得檔案最後修改時間（epoch 秒）"""
    if not os.path.exists(path):
        return None
    return os.path.getmtime(path)

def is_stale(path, hours=12):
    """檢查檔案是否過時"""
    mtime = get_file_mtime(path)
    if mtime is None:
        return None, "FILE_NOT_FOUND"
    age_hours = (datetime.now().timestamp() - mtime) / 3600
    return age_hours, "STALE" if age_hours > hours else "OK"

def format_timestamp(path):
    """取得檔案最後修改時間的字串"""
    mtime = get_file_mtime(path)
    if mtime is None:
        return "NOT_FOUND"
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime('%Y-%m-%d %H:%M')

def check_all(hours=12, dry_run=False):
    """檢查所有 watchlist 並回傳過時的檔案"""
    stale_files = []
    results = []

    for name, path in WATCHLIST_FILES.items():
        age_hours, status = is_stale(path, hours)
        last_updated = format_timestamp(path)
        results.append({
            'name': name,
            'path': path,
            'age_hours': age_hours,
            'status': status,
            'last_updated': last_updated,
        })
        if status == "STALE" or status == "FILE_NOT_FOUND":
            stale_files.append(name)

    # Print results
    print(f"=== Stale Data Check (threshold={hours}h) ===")
    print()
    for r in results:
        flag = "⚠️" if r['status'] == "STALE" else ("❌" if r['status'] == "FILE_NOT_FOUND" else "✅")
        if r['age_hours'] is not None:
            print(f"{flag} {r['name']:<25} {r['age_hours']:>6.1f}h old  (last: {r['last_updated']})")
        else:
            print(f"{flag} {r['name']:<25} {r['status']}")
    print()

    return stale_files, results

def send_telegram_alert(stale_files, results):
    """發送 Telegram 警報"""
    try:
        import telegram
    except ImportError:
        # Try to use openclaw's telegram integration
        pass

    # Build message
    lines = ["⚠️ Tina 系統過時資料警報\n"]
    lines.append(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"過時檔案 ({len(stale_files)}):\n")
    for name in stale_files:
        r = next((x for x in results if x['name'] == name), None)
        if r:
            if r['age_hours'] is not None:
                lines.append(f"• {name}: {r['age_hours']:.1f}h 未更新 (last: {r['last_updated']})")
            else:
                lines.append(f"• {name}: 檔案不存在")

    msg = "\n".join(lines)
    print("=== Telegram Alert ===")
    print(msg)

    # Try to send via openclaw cron notification mechanism
    # The alert will be surfaced through the cron job's announce mechanism
    return msg

def main():
    parser = argparse.ArgumentParser(description='Tina Stale Data Alert')
    parser.add_argument('--check', action='store_true', help='Dry run - check only, no alert')
    parser.add_argument('--hours', type=int, default=12, help='Stale threshold in hours (default: 12)')
    args = parser.parse_args()

    stale_files, results = check_all(hours=args.hours)

    if stale_files:
        print(f"❌ {len(stale_files)} file(s) are stale!")
        if not args.check:
            send_telegram_alert(stale_files, results)
            sys.exit(1)
        else:
            sys.exit(1)
    else:
        print("✅ All watchlist files are fresh!")
        sys.exit(0)

if __name__ == '__main__':
    main()