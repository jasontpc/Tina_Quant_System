"""
Fill remaining 55 symbols using FinMind API for Taiwan stocks.
Then yfinance for US stocks with aggressive rate-limit backoff.
"""
import sqlite3
import time
import requests
from pathlib import Path

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
conn.close()

TARGET = 500
need = TARGET - len(existing)
print(f"Existing: {len(existing)}, need: {need}")

# ── Step 1: Use FinMind API for Taiwan stocks ────────────────────────────────
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM"
BASE_URL = "https://api.finmindtrade.com/api/v4/data"

conn2 = sqlite3.connect(str(DB))
cur2 = conn2.cursor()

def insert_finmind_rows(sym, rows_data):
    """Insert rows from FinMind API response."""
    cnt = 0
    for row in rows_data:
        try:
            cur2.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                (sym, str(row['date'])[:10],
                 float(row['Open']), float(row['High']),
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
            cnt += 1
        except Exception:
            pass
    conn2.commit()
    return cnt

# Try FinMind for each existing TW symbol (to refresh data) and some new ones
# For new symbols, try codes in the 2xxx-9xxx range
tw_codes_to_try = list(range(2000, 9999, 1))
tw_new = [f"{c}.TW" for c in tw_codes_to_try if f"{c}.TW" not in existing][:200]

ok_fm = 0; fail_fm = 0
for sym in tw_new:
    conn3 = sqlite3.connect(str(DB))
    cur3 = conn3.cursor()
    cur3.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur3.fetchone()[0]
    conn3.close()
    if total >= TARGET:
        print(f"TARGET {total} reached!")
        break

    code = sym.replace('.TW', '')
    try:
        resp = requests.get(BASE_URL, params={
            "dataset": "TaiwanStockPrice",
            "data_id": code,
            "start_date": "2022-05-01",
            "token": FINMIND_TOKEN,
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('data'):
                rows = data['data']
                if len(rows) >= 20:
                    n = insert_finmind_rows(sym, rows)
                    ok_fm += 1
                    print(f"  [FM OK] {sym} ({n} rows) total={total+1}")
                else:
                    fail_fm += 1
            else:
                fail_fm += 1
        else:
            fail_fm += 1
    except Exception as e:
        fail_fm += 1

    time.sleep(0.3)

conn2.close()
print(f"FinMind: {ok_fm} added, {fail_fm} failed")

# Check final
conn4 = sqlite3.connect(str(DB))
cur4 = conn4.cursor()
cur4.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_final = cur4.fetchone()[0]
cur4.execute("SELECT COUNT(*) FROM daily_ohlcv")
total_rows = cur4.fetchone()[0]
conn4.close()
print(f"\nFinal: {total_final} symbols, {total_rows} rows")