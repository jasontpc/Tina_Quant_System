import sqlite3
conn = sqlite3.connect('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/master_backtest.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print("Tables:", tables)

# Check decisions table
if 'decisions' in tables:
    c.execute("SELECT created_at, layer1_goals, layer3_market, layer5_decision FROM decisions ORDER BY created_at DESC LIMIT 3")
    rows = c.fetchall()
    print("\nRecent decisions:")
    for r in rows:
        print(f"  {r[0]} | goals={str(r[1])[:60]}... | decision={r[3]}")

# Check trade_log
if 'trade_log' in tables:
    c.execute("SELECT symbol, direction, entry_price, entry_date, status FROM trade_log ORDER BY entry_date DESC LIMIT 10")
    rows = c.fetchall()
    print("\nRecent trades:")
    for r in rows:
        print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}")

# Check portfolio
if 'portfolio' in tables:
    c.execute("SELECT symbol, qty, entry_price, current_price, pnl_pct FROM portfolio ORDER BY entry_date DESC LIMIT 10")
    rows = c.fetchall()
    print("\nPortfolio:")
    for r in rows:
        print(f"  {r[0]} | qty={r[1]} | entry={r[2]} | curr={r[3]} | pnl={r[4]:.2f}%")

conn.close()