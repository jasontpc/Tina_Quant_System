import sqlite3
from datetime import datetime

conn = sqlite3.connect('us_fund_flow.db')
today = datetime.now().strftime('%Y-%m-%d')

print('=== US FUND FLOW REPORT ===')
print()

# Sentiment
cur = conn.execute('SELECT * FROM market_sentiment ORDER BY id DESC LIMIT 1')
row = cur.fetchone()
cols = [c[0] for c in cur.description]
sentiment = dict(zip(cols, row))
print('[MARKET SENTIMENT]')
fg = sentiment['fear_greed_index']
fg_label = sentiment['fear_greed_label']
vix = sentiment['vix']
vix_chg = sentiment['vix_change_pct']
mode = sentiment['market_mode']
ro = sentiment['risk_on_score']
rff = sentiment['risk_off_score']
print('  Fear/Greed: ' + str(fg) + ' (' + fg_label + ')')
print('  VIX: ' + str(round(vix,2)) + ' (' + ('+' if vix_chg > 0 else '') + str(round(vix_chg,2)) + '%)')
print('  Mode: ' + mode + ' (Risk On: ' + str(ro) + ', Risk Off: ' + str(rff) + ')')
print()

# Sector flows
cur = conn.execute('SELECT symbol, sector_name, price, change_pct, rsi, mfi, trend, flow_direction, heatmap_color FROM sector_flow ORDER BY change_pct DESC')
rows = cur.fetchall()

print('[SECTOR FUND FLOWS]')
print('-'*70)
print('Symbol   Sector               Price       Chg%     RSI     MFI Trend       Flow')
print('-'*70)

for row in rows:
    sym, name, price, chg, rsi, mfi, trend, flow, color = row
    sign = '+' if chg > 0 else ''
    emoji = '▲' if chg > 0.5 else '▼' if chg < -0.5 else '-'
    flow_mark = '↑' if flow == 'inflow' else '↓' if flow == 'outflow' else '-'
    print(sym.ljust(8) + ' ' + name[:20].ljust(20) + ' ' + str(round(price,2)).rjust(8) + ' ' + sign + str(round(chg,2)).ljust(6) + '% ' + str(round(rsi,0)).rjust(6) + ' ' + str(round(mfi,0)).rjust(6) + ' ' + trend[:10].ljust(10) + ' ' + flow_mark.ljust(6) + ' ' + emoji)

print()
print('[SUMMARY]')
inflow = [r[0] for r in rows if r[7] == 'inflow']
outflow = [r[0] for r in rows if r[7] == 'outflow']
print('  Inflow sectors: ' + str(len(inflow)) + ' - ' + str(inflow))
print('  Outflow sectors: ' + str(len(outflow)) + ' - ' + str(outflow))

print()
print('[BUY SIGNALS (MFI>60, RSI>50)]')
buy = [(r[0], r[1], r[4], r[5]) for r in rows if r[5] > 60 and r[4] > 50]
if buy:
    for b in buy:
        print('  ' + b[0] + ' ' + b[1] + ': RSI=' + str(round(b[2],0)) + ', MFI=' + str(round(b[3],0)))
else:
    print('  None')

print()
print('[SELL/WATCH (MFI<40, RSI<45)]')
sell = [(r[0], r[1], r[4], r[5]) for r in rows if r[5] < 40 and r[4] < 45]
if sell:
    for s in sell:
        print('  ' + s[0] + ' ' + s[1] + ': RSI=' + str(round(s[2],0)) + ', MFI=' + str(round(s[3],0)))
else:
    print('  None')

conn.close()