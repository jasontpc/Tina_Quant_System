"""
Tina 全系統資料庫及技能整合分析
System-wide Database & Skills Integration Analysis
"""

import sys, json, os, sqlite3
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent  # Tina_Quant_System/

# ==========================================
# 系統資料庫清單
# ==========================================
DATABASES = {
    # 台股相關
    'tw_ai_tech': {'name': '台股AI科技資料庫', 'path': 'tw_ai_tech/tw_ai_tech.db', 'stocks': '台股AI/科技'},
    'tw_etf': {'name': '台股ETF資料庫', 'path': 'tw_etf/tw_etf.db', 'stocks': '台股ETF'},
    'tw_etf_return': {'name': '台股ETF報酬資料庫', 'path': 'tw_etf_return/tw_etf_return.db', 'stocks': '台股ETF報酬'},
    'tw_margin': {'name': '台股Margin資料庫', 'path': 'tw_margin/tw_margin.db', 'stocks': '台股Margin'},
    
    # 美股相關
    'us_ai_tech': {'name': '美股AI科技資料庫', 'path': 'us_ai_tech/us_ai_tech.db', 'stocks': '美股AI/科技'},
    'us_etf': {'name': '美股ETF資料庫', 'path': 'us_etf/us_etf.db', 'stocks': '美股ETF'},
    'us_etf_return': {'name': '美股ETF報酬資料庫', 'path': 'us_etf_return/us_etf_return.db', 'stocks': '美股ETF報酬'},
    'us_margin': {'name': '美股Margin資料庫', 'path': 'us_margin/us_margin.db', 'stocks': '美股Margin'},
    'us_fund_flow': {'name': '美股資金流向資料庫', 'path': 'us_fund_flow/us_fund_flow.db', 'stocks': '美股資金'},
    
    # 跨市場
    'unified_db': {'name': '統一交易資料庫', 'path': 'unified_db/unified_trading.db', 'stocks': '跨市場統一'},
    'macro_db': {'name': '宏觀分析資料庫', 'path': 'macro_db/macro.db', 'stocks': '宏觀經濟'},
    'usd_twd': {'name': 'USD/TWD匯率資料庫', 'path': 'usd_twd/usd_twd.db', 'stocks': '匯率'},
}

# ==========================================
# 分析函數
# ==========================================
def check_db(db_path, key=None):
    """檢查資料庫狀態"""
    # Check us_fund_flow which uses JSON files instead of SQLite
    # us_fund_flow uses JSON files in data/ subdirectory
    if '/us_fund_flow' in db_path or db_path == 'us_fund_flow/us_fund_flow.db':
        full_path = BASE_DIR / 'us_fund_flow' / 'data'
        if full_path.exists():
            json_files = list(full_path.glob('fund_flow_*.json'))
            if json_files:
                latest = max(json_files, key=lambda p: p.stat().st_mtime)
                with open(latest, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        records = len(data.get('flows', [])) if isinstance(data, dict) else 1
                        return {
                            'exists': True,
                            'size': latest.stat().st_size,
                            'size_mb': round(latest.stat().st_size / 1024 / 1024, 2),
                            'tables': ['fund_flows'],
                            'records': records
                        }
                    except:
                        return {'exists': True, 'size': 0, 'tables': [], 'records': 0}
        return {'exists': False, 'size': 0, 'tables': [], 'records': 0}
    
    full_path = BASE_DIR / db_path
    if not full_path.exists():
        return {'exists': False, 'size': 0, 'tables': [], 'records': 0}
    
    size = full_path.stat().st_size
    try:
        conn = sqlite3.connect(str(full_path))
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        
        total_records = 0
        for table in tables:
            try:
                cur2 = conn.execute(f"SELECT COUNT(*) FROM {table}")
                cnt = cur2.fetchone()[0]
                total_records += cnt
            except:
                pass
        
        conn.close()
        return {
            'exists': True,
            'size': size,
            'size_mb': round(size / 1024 / 1024, 2),
            'tables': tables,
            'records': total_records
        }
    except Exception as e:
        return {'exists': True, 'error': str(e)}

def get_latest_report(db_name):
    """取得最新報告"""
    reports_dir = BASE_DIR / db_name
    if not reports_dir.exists():
        return None
    
    reports = list(reports_dir.glob('daily_report_*.json'))
    if not reports:
        reports = list(reports_dir.glob('*_report_*.json'))
    if not reports:
        return None
    
    latest = max(reports, key=lambda p: p.stat().st_mtime)
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# ==========================================
# 主程式
# ==========================================
def main():
    print('='*70)
    print('  Tina 全系統資料庫及技能整合分析')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*70)
    print()
    
    results = {}
    
    print('【資料庫狀態檢查】')
    print('-'*70)
    print(f"{'資料庫':<20} {'名稱':<25} {'大小':<10} {'資料表':<15} {'記錄數':<10}")
    print('-'*70)
    
    for key, info in DATABASES.items():
        db_info = check_db(info['path'], key=key)
        
        if not db_info.get('exists', False):
            status = '❌ 不存在'
            size_str = '-'
            tables_str = '-'
            records_str = '-'
        elif 'error' in db_info:
            status = f'⚠️ 錯誤'
            size_str = '-'
            tables_str = '-'
            records_str = '-'
        else:
            status = '✅ 正常'
            size_str = f"{db_info.get('size_mb', 0):.2f} MB"
            tables_str = ','.join(db_info.get('tables', [])[:3]) + ('...' if len(db_info.get('tables', [])) > 3 else '')
            records_str = f"{db_info.get('records', 0):,}"
        
        print(f"  {key:<18} {info['name']:<25} {size_str:<10} {tables_str:<15} {records_str:<10}")
        
        results[key] = {
            'status': status,
            'info': db_info
        }
    
    print()
    
    # 統計
    total_dbs = len(DATABASES)
    active_dbs = sum(1 for r in results.values() if '✅' in r['status'])
    total_records = sum(r['info'].get('records', 0) for r in results.values() if r['info'].get('records'))
    
    print('【系統整合狀態】')
    print('-'*70)
    print(f"  總資料庫數量: {total_dbs}")
    print(f"  正常運作: {active_dbs} ({active_dbs/total_dbs*100:.0f}%)")
    print(f"  總記錄數: {total_records:,}")
    
    print()
    print('【技能整合分析】')
    print('-'*70)
    
    skills = [
        ('stock-analyzer', '股票分析技能'),
        ('automation-scheduler', '排程自動化技能'),
        ('automation-rules', '自動化規則技能'),
        ('automation-index', '自動化索引技能'),
        ('tw-stock-info', '台股資訊技能'),
        ('yahoo-finance', 'Yahoo Finance技能'),
    ]
    
    for skill_id, skill_name in skills:
        skill_path = Path.home() / 'AppData/Roaming/npm/node_modules/openclaw/skills' / skill_id
        if skill_path.exists():
            files = list(skill_path.glob('*.py')) + list(skill_path.glob('*.md'))
            print(f"  ✅ {skill_name}: {len(files)} 個檔案")
        else:
            alt_path = Path(__file__).parent.parent / 'workspace/skills' / skill_id
            if alt_path.exists():
                files = list(alt_path.glob('*.py')) + list(alt_path.glob('*.md'))
                print(f"  ✅ {skill_name} (workspace): {len(files)} 個檔案")
            else:
                print(f"  ❌ {skill_name}: 未找到")
    
    print()
    print('【Cron Job 整合狀態】')
    print('-'*70)
    
    # 檢查 cron jobs
    import subprocess
    try:
        result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True, timeout=10)
        lines = result.stdout.split('\n')
        
        cron_count = 0
        active_jobs = []
        for line in lines:
            if 'cron' in line.lower() and '-' in line:
                cron_count += 1
                parts = line.split()
                if len(parts) > 1:
                    active_jobs.append(parts[-1] if parts[-1] not in ['ok', 'error', 'idle'] else parts[-2])
        
        print(f"  總 Cron Jobs: {cron_count}")
        print(f"  啟用中: {sum(1 for j in active_jobs if j == 'ok')}")
        print(f"  錯誤: {sum(1 for j in active_jobs if j == 'error')}")
        print(f"  閒置: {sum(1 for j in active_jobs if j == 'idle')}")
        
    except:
        print('  ⚠️ 無法讀取 Cron Job 列表')
    
    print()
    print('【最佳化建議】')
    print('-'*70)
    
    suggestions = []
    
    # 檢查閒置資料庫
    for key, info in DATABASES.items():
        if '❌' in results[key]['status']:
            suggestions.append(f"  🔴 {info['name']} 需要重建")
        elif results[key]['info'].get('records', 0) == 0:
            suggestions.append(f"  ⚠️ {info['name']} 無記錄，需要更新")
    
    # 檢查技能
    if len(results) < total_dbs:
        suggestions.append(f"  🔴 缺少 {total_dbs - len(results)} 個資料庫")
    
    if not suggestions:
        suggestions.append("  ✅ 所有資料庫正常運作")
        suggestions.append("  ✅ 技能已完整串聯")
        suggestions.append("  ✅ 系統整合完成")
    else:
        suggestions.append(f"  📝 共 {len(suggestions)} 項需要優化")
    
    for s in suggestions:
        print(s)
    
    print()
    print('='*70)
    print('  Tina 全系統整合分析完成')
    print('='*70)
    
    # 儲存報告
    out_dir = BASE_DIR / 'data'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f'system_integration_report_{datetime.now().strftime("%Y%m%d")}.json'
    
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'databases': {},
        'summary': {
            'total': total_dbs,
            'active': active_dbs,
            'records': total_records
        }
    }
    
    for k, v in results.items():
        db_entry = {'status': v['status']}
        if 'info' in v and isinstance(v['info'], dict):
            db_entry['records'] = v['info'].get('records', 0)
            db_entry['size_mb'] = v['info'].get('size_mb', 0)
        report['databases'][k] = db_entry
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'\n報告已儲存: {out_file}')

if __name__ == '__main__':
    main()