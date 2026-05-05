import yfinance as yf
import sqlite3
from datetime import datetime

# US stock registry updater - fetches company info and market cap
stocks = ['NVDA','AMD','INTC','TSM','DLO','GEN','RKLB','DXCM','COIN','SOFI',
          'SMCI','PATH','GTLB','U','BILL','ESTC','NET','D','BMY','SO',
          'VEA','VTI','VOO','QQQ','BND']

db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_stock_registry.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('Updating US stock registry...')
for symbol in stocks:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        name = info.get('longName', info.get('shortName', ''))
        sector = info.get('sector', 'N/A')
        exchange = info.get('exchange', 'N/A')
        market_cap = info.get('marketCap', 0)
        
        # Classify market cap
        if market_cap > 200e9:
            cap_label = 'Mega Cap'
        elif market_cap > 10e9:
            cap_label = 'Large Cap'
        elif market_cap > 2e9:
            cap_label = 'Mid Cap'
        else:
            cap_label = 'Small Cap'

        c.execute('''INSERT OR REPLACE INTO us_stocks VALUES (?,?,?,?,?,?,?)''',
            (symbol, name, '', sector, exchange, cap_label, datetime.now().strftime('%Y-%m-%d')))
        print(f'  {symbol}: {name} ({cap_label})')
    except Exception as e:
        print(f'  {symbol}: Error - {e}')

conn.commit()
c.execute('SELECT COUNT(*) FROM us_stocks')
print(f'Total in registry: {c.fetchone()[0]}')
conn.close()