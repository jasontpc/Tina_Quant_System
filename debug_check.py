from pathlib import Path
import json

BASE_DIR = Path('.')
key = 'us_fund_flow'
db_path = 'us_fund_flow/us_fund_flow.db'

# Simulate check_db function
print(f'key={key}, db_path={db_path}')
print(f'Checking if key == us_fund_flow: {key == "us_fund_flow"}')

if key == 'us_fund_flow':
    full_path = BASE_DIR / 'us_fund_flow' / 'data'
    print(f'full_path: {full_path}')
    print(f'exists: {full_path.exists()}')
    if full_path.exists():
        json_files = list(full_path.glob('fund_flow_*.json'))
        print(f'files: {[f.name for f in json_files]}')
        if json_files:
            latest = max(json_files, key=lambda p: p.stat().st_mtime)
            with open(latest, 'r', encoding='utf-8') as f:
                data = json.load(f)
            records = len(data.get('flows', [])) if isinstance(data, dict) else 1
            print(f'records: {records}')