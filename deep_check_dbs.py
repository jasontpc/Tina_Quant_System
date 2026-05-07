import sqlite3, os

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

for db_name in ['finmind.db', 'limitup.db', 'rsi.db']:
    path = os.path.join(data_dir, db_name)
    print(f'\n=== {db_name} ({os.path.getsize(path):,} bytes) ===')
    if not os.path.exists(path):
        print('  NOT FOUND'); continue
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            print('  (no tables)')
        for t in tables:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            mx_date = conn.execute(f'SELECT MAX(date) FROM "{t}"').fetchone()[0] if cnt > 0 else 'N/A'
            print(f'  {t}: {cnt:,} rows, last_date={mx_date}')
        conn.close()
    except Exception as e:
        print(f'  ERROR: {e}')

# Also check what's in teams/maggy/
print('\n=== teams/maggy/ ===')
mg_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy'
if os.path.exists(mg_dir):
    for f in os.listdir(mg_dir):
        print(f'  {f}')
else:
    print('  (dir not found)')

# Check maggy/db path
print('\n=== maggy.db full scan ===')
for root, dirs, files in os.walk(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'):
    if 'maggy.db' in files:
        full = os.path.join(root, 'maggy.db')
        sz = os.path.getsize(full)
        print(f'  {full} ({sz:,} bytes)')