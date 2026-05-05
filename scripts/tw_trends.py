import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

TW = ['2330','2382','2454','2317','3034','3665','2344','6442','3450','4908']

print('=== StockTwits TW Stocks ===')
conn = sqlite3.connect('data/stocktwits_sentiment.db')
c = conn.cursor()
c.execute('SELECT ticker, msg_count, bullish_count, bearish_count, sentiment_avg FROM ticker_stats ORDER BY msg_count DESC LIMIT 20')
for r in c.fetchall():
    if r[0] in TW or any(tw in r[0] for tw in ['2330','2382','2454','2317']):
        net = r[2]-r[3]
        bar = '+'*min(net,8) if net>0 else '-'*min(-net,8)
        print('  %s %3d msgs B%2d Br%2d %5.1f %s' % (r[0],r[1],r[2],r[3],r[4],bar))
conn.close()

print()
print('=== Reddit TW Stocks ===')
conn = sqlite3.connect('data/reddit_sentiment.db')
c = conn.cursor()
c.execute('SELECT ticker, post_count, total_score, sentiment_avg FROM tickers ORDER BY total_score DESC LIMIT 20')
for r in c.fetchall():
    print('  %s %d posts %d pts sent=%.1f' % (r[0],r[1],r[2],r[3]))
conn.close()

print()
print('=== Tavily TW Coverage ===')
conn = sqlite3.connect('data/social_sentiment.db')
c = conn.cursor()
c.execute('SELECT ticker, article_count, sentiment_avg FROM ticker_stats ORDER BY article_count DESC LIMIT 20')
for r in c.fetchall():
    print('  %s %d arts sent=%.1f' % (r[0],r[1],r[2]))
conn.close()
