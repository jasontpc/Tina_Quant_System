import sqlite3
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Analyze institutional data coverage
# Check which symbols have null institutional data
cur.execute('''
SELECT symbol, COUNT(*) as records,
  SUM(CASE WHEN foreign_net IS NULL OR trust_net IS NULL THEN 1 ELSE 0 END) as null_inst,
  SUM(CASE WHEN foreign_net = 0 AND trust_net = 0 THEN 1 ELSE 0 END) as zero_inst
FROM MarketData
GROUP BY symbol
ORDER BY null_inst DESC, zero_inst DESC
LIMIT 20
''')
coverage = cur.fetchall()
print('Symbols with institutional data issues:')
print('Symbol | Records | Null Inst | Zero Inst')
print('-------|---------|-----------|----------')
for row in coverage:
    print(f'{row[0]:<8} {row[1]:<8} {row[2]:<10} {row[3]}')

# Check failure_log stocks coverage
print('\n\nFailure log stocks institutional coverage:')
failure_stocks = ['3231', '3017', '2379', '2345', '3717', '3008']
for code in failure_stocks:
    cur.execute('''
    SELECT symbol, COUNT(*) as records,
      SUM(foreign_net) as total_foreign,
      SUM(trust_net) as total_trust
    FROM MarketData 
    WHERE symbol = ?
    ''', (code,))
    row = cur.fetchone()
    if row[1]:
        print(f'{code}: {row[1]} records, foreign_net sum: {row[2]}, trust_net sum: {row[3]}')
    else:
        print(f'{code}: NOT FOUND in MarketData')

# Get list of all symbols
cur.execute("SELECT DISTINCT symbol FROM MarketData ORDER BY symbol")
all_symbols = [r[0] for r in cur.fetchall()]
print(f'\nAll {len(all_symbols)} symbols in MarketData:')
print(all_symbols)

conn.close()