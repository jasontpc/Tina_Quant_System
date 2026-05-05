import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime

DB = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db'

def add_00891():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Check if 00891 already in Assets
    c.execute("SELECT symbol FROM Assets WHERE symbol='00891'")
    if c.fetchone():
        print('00891 already in Assets')
    else:
        c.execute("INSERT INTO Assets (symbol, name) VALUES ('00891', '中信金特')")
        print('Added 00891 to Assets')
    
    # Fetch 00891 data from yfinance
    print('Fetching 00891 data from yfinance...')
    ticker = yf.Ticker('00891.TW')
    df = ticker.history(period='1y', auto_adjust=True)
    
    if df is None or len(df) == 0:
        print('Failed to fetch 00891 data')
        conn.close()
        return
    
    df = df.dropna(subset=['Close'])
    print(f'Fetched {len(df)} rows for 00891')
    
    # Check existing data range
    c.execute("SELECT MIN(date), MAX(date) FROM MarketData WHERE symbol='00891'")
    row = c.fetchone()
    if row[0]:
        print(f'Existing 00891 data: {row[0]} to {row[1]}')
    else:
        print('No existing 00891 data')
    
    # Insert data
    count = 0
    for date, row in df.iterrows():
        date_str = str(date)[:10]
        close = row['Close']
        high = row['High']
        low = row['Low']
        volume = row['Volume']
        
        c.execute("""INSERT OR IGNORE INTO MarketData 
                    (symbol, date, close, high, low, volume, foreign_net, trust_net, foreign_consecutive, trust_consecutive)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0)""",
                 ('00891', date_str, close, high, low, volume))
        if c.rowcount > 0:
            count += 1
    
    conn.commit()
    print(f'Inserted {count} new rows for 00891')
    
    # Verify
    c.execute("SELECT COUNT(*) FROM MarketData WHERE symbol='00891'")
    print(f'Total 00891 rows: {c.fetchone()[0]}')
    
    conn.close()

if __name__ == '__main__':
    add_00891()
