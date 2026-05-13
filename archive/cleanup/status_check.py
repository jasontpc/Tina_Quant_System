import sqlite3, requests
conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

# Ollama models
print('=== Ollama Models ===')
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=5)
    models = r.json().get('models', [])
    for m in models:
        size_gb = m.get('size', 0) // (1024**3)
        print(f'  {m["name"]} ({size_gb}GB)')
except Exception as e:
    print(f'  Error: {e}')

# backtest quality
print()
print('=== backtest_reports quality ===')
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0.5')
print(f'Sharpe > 0.5: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.0')
print(f'Sharpe > 1.0: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.5')
print(f'Sharpe > 1.5: {c.fetchone()[0]}')

# wisdom_corrections
print()
print('=== wisdom_corrections ===')
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
print(f'Total corrections: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
print(f'High confidence (>=0.8): {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence < 0.5')
print(f'Low confidence (<0.5): {c.fetchone()[0]}')

# wisdom_logs weight decay
print()
print('=== wisdom_logs weight decay ===')
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0')
print(f'Underweight (<1.0): {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight > 2.0')
print(f'Strong (>2.0): {c.fetchone()[0]}')

# signals
print()
print('=== Approved Signals ===')
c.execute('SELECT symbol, score, sharpe_30d, signal_tag FROM signals_log WHERE approved=1 ORDER BY score DESC')
for row in c.fetchall():
    print(f'  {row[0]}: score={row[1]} sharpe30d={row[2]} tag={row[3]}')

conn.close()