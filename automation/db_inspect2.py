import sqlite3
conn = sqlite3.connect('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/master_backtest.db')
c = conn.cursor()
c.execute("SELECT * FROM trade_archive ORDER BY entry_date DESC LIMIT 20")
rows = c.fetchall()
cols = [desc[0] for desc in c.description]
print("trade_archive columns:", cols)
print(f"\nRecent trades (n={len(rows)}):")
for r in rows:
    d = dict(zip(cols, r))
    print(f"  {d['symbol']} | {d['entry_price']} | date={d['entry_date']} | exit={d.get('exit_price','--')} | ret={d.get('return_pct','--')}% | {d['status'] if 'status' in d else d.get('exit_reason','--')}")
conn.close()