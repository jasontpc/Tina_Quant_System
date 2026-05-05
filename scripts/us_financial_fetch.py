import yfinance as yf
import sqlite3
import os
from datetime import datetime

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
db_path = os.path.join(data_dir, 'financial_history.db')

def calc_margin(gross, revenue):
    if revenue and revenue > 0:
        return gross / revenue
    return None

us_stocks = ['DLO', 'GEN', 'RKLB', 'DXCM', 'COIN', 'SMCI', 'SOFI']

print('=== 擴充美股財報資料 ===')
print(f'Target DB: {db_path}')
print(f'Stocks: {us_stocks}')
print()

# Init DB if needed
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS quarterly_financials
    (stock TEXT, quarter TEXT, revenue REAL, gross_profit REAL,
     operating_income REAL, net_income REAL, eps REAL,
     gross_margin REAL, operating_margin REAL, net_margin REAL,
     fetched_at TEXT)''')
conn.commit()

for ticker in us_stocks:
    print(f'Fetching {ticker}...')
    try:
        tk = yf.Ticker(ticker)
        # Get quarterly income statement
        q = tk.quarterly_income_stmt
        if q is None or q.empty:
            print(f'  {ticker}: No quarterly data')
            continue
        
        # Get the last 8 quarters
        quarters = q.columns[:8]
        count = 0
        for col in quarters:
            try:
                date = str(col.to_pydatetime().date())[:10]
                revenue = q.loc['Total Revenue', col] if 'Total Revenue' in q.index else None
                gross_profit = q.loc['Gross Profit', col] if 'Gross Profit' in q.index else None
                operating_income = q.loc['Operating Income', col] if 'Operating Income' in q.index else None
                net_income = q.loc['Net Income', col] if 'Net Income' in q.index else None
                eps = q.loc['Basic EPS', col] if 'Basic EPS' in q.index else (q.loc['Diluted EPS', col] if 'Diluted EPS' in q.index else None)
                
                gross_margin = calc_margin(gross_profit, revenue)
                op_margin = calc_margin(operating_income, revenue)
                net_margin = calc_margin(net_income, revenue)
                
                if revenue and revenue > 0:
                    c.execute('''INSERT OR REPLACE INTO quarterly_financials
                        (stock, quarter, revenue, gross_profit, operating_income, net_income, eps,
                         gross_margin, operating_margin, net_margin, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (ticker, date, revenue, gross_profit, operating_income, net_income, eps,
                         gross_margin, op_margin, net_margin, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    count += 1
            except Exception as e:
                pass
        
        conn.commit()
        print(f'  {ticker}: {count} quarters saved')
    except Exception as e:
        print(f'  {ticker}: Error - {e}')

# Summary
c.execute('SELECT stock, COUNT(*) FROM quarterly_financials GROUP BY stock')
print()
print('=== Summary ===')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]} quarters')
conn.close()
print('Done.')