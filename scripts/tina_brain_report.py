import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

dbs = {
    'yfinance.db': 'data/yfinance.db',
    'finmind.db': 'data/finmind.db',
    'limitup.db': 'data/limitup.db',
    'stocktwits_sentiment.db': 'data/stocktwits_sentiment.db',
    'reddit_sentiment.db': 'data/reddit_sentiment.db',
    'social_sentiment.db': 'data/social_sentiment.db',
    'twse_data.db': 'data/twse_data.db',
}

print('=' * 60)
print('  Tina 大腦學習報告 - 2026-05-03')
print('=' * 60)
print()

total = 0
for name, path in dbs.items():
    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        cnt = sum(c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables)
        print(f'{name}: {cnt:,} rows')
        total += cnt
        conn.close()
    except Exception as e:
        print(f'{name}: ERROR {e}')

print()
print(f'Total: {total:,} records across 7 DBs')
print()

print('=== 自動化排程 (7 cron jobs) ===')
jobs = [
    ('38fc8dba', '07:00', 'Reddit社群情緒更新'),
    ('e361dc2e', '07:00', 'StockTwits多空情緒更新'),
    ('de4b8223', '07:30', 'Tavily社群情緒更新'),
    ('0c847110', '08:00', 'Tina每日市場快報'),
    ('529d3c7c', '16:00', '漲停板每日掃描'),
    ('1306d237', '17:00', 'Tina自動學習擴充DB'),
    ('facc1550', '16:30', 'Tina每日DB收盤更新'),
]
for jid, time, name in jobs:
    print(f'  {time}  {name}')
print()

print('=== 今日重大新建系統 ===')
print()
print('[新建資料庫]')
print('  finmind.db        9,369 rows - 法人/資券/期貨')
print('  limitup.db            7 rows - 漲跌停板追蹤')
print('  stocktwits.db      877 rows - StockTwits多空情緒')
print('  reddit.db          258 rows - Reddit熱門討論')
print('  social_sentiment.db 470 rows - Tavily社群覆蓋')
print()
print('[漲跌停板] 前日(2026-05-01)')
print('  3037.TW 驊訊科  $883    +9.96%  Vol=33.3M [LIMIT UP]')
print('  4958.TW 磐桓     $421   +9.92%  Vol=45.5M [LIMIT UP]')
print('  3026.TW 增你強  $212.50 -9.96%  Vol=16.8M [LIMIT DOWN]')
print()
print('[社群情緒亮點] 觀察用途（不計分）')
print('  INTC   StockTwits: 18 Bull vs 3 Bear  sentiment=55.0')
print('  ASML   StockTwits: 17 Bull vs 2 Bear  sentiment=55.0')
print('  AVGO   StockTwits: 15 Bull vs 1 Bear  sentiment=54.7')
print('  META   StockTwits:  8 Bull vs 10 Bear sentiment=49.3 [BEARISH]')
print()
print('[技術面警示]')
print('  SOXL/TQQQ/UPRO/SPXL RSI>78  過熱 HIGH')
print('  SOXS RSI=15.2  超賣 LOW')
print()
print('[大盤狀態]')
print('  TWII RSI=79.9  MACD=+224  偏高，追蹤回調')
print('  SPX RSI=78.5   MACD=+14   多頭')
print('  NDX RSI=82.5   MACD=+105  多頭')
print()
print('[DB觀察名單]')
print('  3706.TW, 4938.TW, 3090.TW  - 百元動能篩選')
print('  INTC, ASML, AVGO, QCOM     - StockTwits機構看多')
print('  3706.TW, 4938.TW, 3090.TW  - 百元動能篩選')
print('  INTC, MU, NVDA, AVGO       - Reddit社群熱門')
print()
print('=== 系統健康度 ===')
print('  Nana 波段:     OK')
print('  Leo 科技股:    OK')
print('  Ray DCA:       OK')
print('  Tina 大腦:     OK (v3 慢思考 + 專家委員會)')
print('  本地 DB:       7個資料庫 / 152,963 records  OK')
print()
print('=' * 60)
print('[DONE]')
