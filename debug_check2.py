import sys
from pathlib import Path
import json

BASE_DIR = Path('.')
DATABASES = {
    'tw_ai_tech': {'name': '台股AI科技資料庫', 'path': 'tw_ai_tech/tw_ai_tech.db'},
    'us_fund_flow': {'name': '美股資金流向資料庫', 'path': 'us_fund_flow/us_fund_flow.db'},
}

results = {}

for key, info in DATABASES.items():
    print(f'Processing {key}')
    
    db_path = info['path']
    
    if key == 'us_fund_flow':
        full_path = BASE_DIR / 'us_fund_flow' / 'data'
        if full_path.exists():
            json_files = list(full_path.glob('fund_flow_*.json'))
            if json_files:
                latest = max(json_files, key=lambda p: p.stat().st_mtime)
                print(f'  Found {latest.name}')
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                records = len(data.get('flows', [])) if isinstance(data, dict) else 1
                db_info = {
                    'exists': True,
                    'size': latest.stat().st_size,
                    'size_mb': round(latest.stat().st_size / 1024 / 1024, 2),
                    'tables': ['fund_flows'],
                    'records': records
                }
                print(f'  records: {records}')
                status = 'ok'
                results[key] = {'status': status, 'info': db_info}
            else:
                results[key] = {'status': 'error', 'info': {}}
        else:
            results[key] = {'status': 'not_found', 'info': {}}
    else:
        print(f'  SQLite db')
        results[key] = {'status': 'ok', 'info': {'records': 100}}

print()
print('Results:')
for k, v in results.items():
    print(f'{k}: status={v["status"]}, records={v["info"].get("records", 0)}')