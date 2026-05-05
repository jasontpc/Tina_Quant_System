"""
台股 Margin 每日更新腳本
TW Margin Daily Update
"""

import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

from tw_margin_database import init_db, update_all, print_report, get_report, get_all_alerts
from datetime import datetime
import json

def main():
    print('='*60)
    print('  TW Margin 資料庫每日更新')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)
    print()
    
    # 初始化
    init_db()
    
    # 更新數據
    result = update_all()
    
    # 輸出報告
    print_report()
    
    # 風險警報
    alerts = get_all_alerts()
    if alerts:
        print()
        print('【最新警報】')
        for a in alerts[:5]:
            emoji = '🔴' if a['severity'] == 'HIGH' else '⚠️'
            print(f"  {emoji} {a['symbol']} - {a['message']}")
    
    # 儲存報告
    out_file = Path(__file__).parent / f'daily_report_{datetime.now().strftime("%Y%m%d")}.json'
    report = get_report()
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'report': {
                'high_risk': len(report['high']),
                'medium_risk': len(report['medium']),
                'low_risk': len(report['low']),
                'total': report['total']
            },
            'alerts': alerts,
            'updated': result['updated']
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\n報告已儲存: {out_file}')
    print('完成!')

if __name__ == '__main__':
    main()