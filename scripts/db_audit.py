import sqlite3
from datetime import date

dbs = {
    'yfinance.db': 'data/yfinance.db',
    'finmind.db': 'data/finmind.db',
    'reddit_sentiment.db': 'data/reddit_sentiment.db',
    'social_sentiment.db': 'data/social_sentiment.db',
    'limitup.db': 'data/limitup.db',
    'twse_data.db': 'data/twse_data.db',
}

print('=== Tina 本地資料庫全景 Audit ===')
print()

total_overall = 0
for name, path in dbs.items():
    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        table_info = []
        table_total = 0
        for t in tables:
            try:
                cnt = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                table_total += cnt
            except Exception:
                pass
        print(f'{name}: {len(tables)} tables, {table_total:,} rows')
        total_overall += table_total
        conn.close()
    except Exception as e:
        print(f'{name}: ERROR {e}')

print()
print(f'Total records across all DBs: {total_overall:,}')

# Hot tickers from today's sentiment
print()
print('=== 今日社群熱門 ticker ===')
conn = sqlite3.connect('data/reddit_sentiment.db')
c = conn.cursor()
today = date.today().strftime('%Y-%m-%d')
rows = c.execute('''
    SELECT ticker, post_count, total_score, sentiment_avg
    FROM tickers WHERE last_mentioned=? ORDER BY total_score DESC LIMIT 10
''', (today,)).fetchall()
if rows:
    print(f'{"Ticker":<10} {"Posts":>6} {"Score":>8} {"Sentiment":>9}')
    print('-' * 40)
    for r in rows:
        print(f'{r[0]:<10} {r[1]:>6} {r[2]:>8} {r[3]:>9.2f}')
conn.close()

conn = sqlite3.connect('data/social_sentiment.db')
c = conn.cursor()
rows = c.execute('''
    SELECT ticker, article_count, positive_count, negative_count, sentiment_avg
    FROM ticker_stats ORDER BY sentiment_avg DESC LIMIT 10
''').fetchall()
if rows:
    print()
    print(f'{"Ticker":<10} {"Articles":>9} {"Pos":>5} {"Neg":>5} {"Sentiment":>9}')
    print('-' * 45)
    for r in rows:
        print(f'{r[0]:<10} {r[1]:>9} {r[2]:>5} {r[3]:>5} {r[4]:>9.1f}')
conn.close()

# Limitup stocks
conn = sqlite3.connect('data/limitup.db')
c = conn.cursor()
rows = c.execute('''
    SELECT symbol, close, change_pct, volume, type
    FROM limitup ORDER BY change_pct DESC LIMIT 10
''').fetchall()
if rows:
    print()
    print(f'{"Symbol":<12} {"Close":>8} {"Change%":>9} {"Vol":>12} Type')
    print('-' * 55)
    for r in rows:
        print(f'{r[0]:<12} {r[1]:>8.2f} {r[2]*100:>+8.2f}% {r[3]:>12,} {r[4]}')
conn.close()
