# -*- coding: utf-8 -*-
"""
DB Schema Auditor — 審計全系統所有 DB 的結構
============================================
目標：
1. 列出所有 DB 的 tables + schemas
2. 找出每個 table 的主要用途
3. 找出哪些 table 缺少索引
4. 找出哪些 table 與記憶系統有關聯

輸出：stores/db_audit_report.json
"""

import sqlite3, json, os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_FILE = BASE_DIR / 'stores' / 'db_audit_report.json'

DATA_DIR.mkdir(exist_ok=True)

DB_SCHEMAS = {}

for db_file in sorted(DATA_DIR.glob('*.db')):
    try:
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        
        # Get tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        
        db_info = {
            'tables': {},
            'size_mb': round(db_file.stat().st_size / 1e6, 1),
            'errors': []
        }
        
        for tbl in tables:
            try:
                # Get schema
                cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tbl}'")
                schema = cur.fetchone()[0] or ''
                
                # Get row count
                cur.execute(f"SELECT COUNT(*) FROM [{tbl}]")
                count = cur.fetchone()[0]
                
                # Get columns
                cur.execute(f"PRAGMA table_info([{tbl}])")
                cols = [{'name': r[1], 'type': r[2]} for r in cur.fetchall()]
                
                # Get indexes
                cur.execute(f"PRAGMA index_list([{tbl}])")
                indexes = [r[1] for r in cur.fetchall()]
                
                db_info['tables'][tbl] = {
                    'rows': count,
                    'schema': schema[:200],
                    'columns': cols,
                    'indexes': indexes
                }
            except Exception as e:
                db_info['tables'][tbl] = {'error': str(e)}
        
        DB_SCHEMAS[db_file.name] = db_info
        conn.close()
        print(f'OK: {db_file.name} ({db_info["size_mb"]}MB) {len(db_info["tables"])} tables')
    except Exception as e:
        DB_SCHEMAS[db_file.name] = {'error': str(e)}
        print(f'ERROR: {db_file.name}: {e}')

# Save report
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump(DB_SCHEMAS, f, ensure_ascii=False, indent=2)

print(f'\nReport saved: {REPORT_FILE}')

# Summary
print('\n=== DB Summary ===')
for name, info in sorted(DB_SCHEMAS.items(), key=lambda x: -x[1].get('size_mb', 0)):
    if 'error' in info:
        print(f'  {name}: ERROR')
    else:
        tables = list(info['tables'].keys())
        print(f'  {name}: {info["size_mb"]}MB, {len(tables)} tables — {tables[:5]}')