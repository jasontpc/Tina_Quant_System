import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3, json, time

conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

# Taleb demo
c.execute('INSERT INTO wisdom_corrections (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    (0, 'WEB_SOURCE', '[TALEB] Fat-tail risk warning: current market volatility underestimated',
     json.dumps({'source': 'manual_demo', 'insight': 'Taleb: Markets are fragile, increase tail protection when VIX > 25', 'action': 'Reduce position by 20% when volatility spikes'}),
     0.85, json.dumps({'source': 'web_learner', 'type': 'TALEB'}), time.strftime('%Y-%m-%d %H:%M:%S')))

conn.commit()

c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE symbol=?', ('WEB_SOURCE',))
count = c.fetchone()[0]
print(f'Web source count: {count}')

c.execute('SELECT diagnosis, confidence FROM wisdom_corrections WHERE symbol=? ORDER BY id DESC LIMIT 1', ('WEB_SOURCE',))
row = c.fetchone()
if row:
    print(f'Latest: {row[0][:80]} (conf={row[1]})')

conn.close()
print('Done')