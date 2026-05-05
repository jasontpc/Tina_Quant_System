import yfinance as yf
import sqlite3
from datetime import datetime

# Target stocks for financial data
stocks = ['DLO', 'GEN', 'RKLB', 'DXCM']
db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\financial_history.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

results = []
for symbol in stocks:
    try:
        ticker = yf.Ticker(symbol)
        # Get quarterly income stmt
        df = ticker.quarterly_income_stmt
        if df is None or df.empty:
            print(f'{symbol}: No quarterly data')
            continue
        
        # Transpose: columns are dates, rows are metrics
        for col in df.columns:
            quarter = col.strftime('%Y-%m')
            try:
                revenue = float(df.loc['Total Revenue', col]) if 'Total Revenue' in df.index else None
                gross_profit = float(df.loc['Gross Profit', col]) if 'Gross Profit' in df.index else None
                operating_income = float(df.loc['Operating Income', col]) if 'Operating Income' in df.index else None
                net_income = float(df.loc['Net Income', col]) if 'Net Income' in df.index else None
                eps = float(df.loc['Basic EPS', col]) if 'Basic EPS' in df.index else None
            except:
                print(f'{symbol} Q{quarter}: parse error')
                continue

            gross_margin = (gross_profit / revenue * 100) if (gross_profit and revenue) else None
            op_margin = (operating_income / revenue * 100) if (operating_income and revenue) else None
            net_margin = (net_income / revenue * 100) if (net_income and revenue) else None

            c.execute('''INSERT OR REPLACE INTO quarterly_financials 
                (stock, quarter, revenue, gross_profit, operating_income, net_income, eps,
                 gross_margin, operating_margin, net_margin, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (symbol, quarter, revenue, gross_profit, operating_income, net_income, eps,
                 gross_margin, op_margin, net_margin, datetime.now().strftime('%Y-%m-%d %H:%M')))
            results.append(f'{symbol} Q{quarter}: rev={revenue:.0f} gross={gross_margin:.1f}% op={op_margin:.1f}% net={net_margin:.1f}%')
    except Exception as e:
        print(f'{symbol} error: {e}')

conn.commit()

# Summary
c.execute('SELECT stock, COUNT(*) FROM quarterly_financials GROUP BY stock ORDER BY stock')
print('=== Financial DB Coverage ===')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]} quarters')
print(f'Total new records: {len(results)}')
conn.close()