# -*- coding: utf-8 -*-
"""
US Stock News Crawler
抓取美股新聞並做情緒分析
"""

import requests
import sqlite3
import yfinance as yf
import sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = f'{DATA_DIR}\\news_sentiment.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            source TEXT,
            title TEXT,
            content TEXT,
            sentiment REAL,
            related_stocks TEXT,
            url TEXT,
            fetched_at TEXT
        )
    ''')
    
    conn.commit()
    return conn

def simple_sentiment(text):
    """簡單情緒分析（關鍵字法）"""
    pos = ['漲', '突破', '新高', '利多', '成長', '優於', '買進', '佳', '看好', '爆發', '大漲', '強勁', '超標', '成長', 'beats', 'bullish', 'upgrade', 'gain', 'rally', 'soar', 'jump']
    neg = ['跌', '跌破', '新低', '利空', '衰退', '不如', '賣出', '虧', '看淡', '崩', '大跌', '疲弱', '未達', '下滑', 'miss', 'bearish', 'downgrade', 'fall', 'drop', 'plunge', 'cut']
    
    text_lower = text.lower()
    pos_count = sum(1 for p in pos if p.lower() in text_lower)
    neg_count = sum(1 for n in neg if n.lower() in text_lower)
    
    if pos_count > neg_count:
        return min(1.0, 0.3 + (pos_count - neg_count) * 0.15)
    elif neg_count > pos_count:
        return max(-1.0, -0.3 - (neg_count - pos_count) * 0.15)
    else:
        return 0.0

def fetch_yfinance_news(ticker_symbol, conn):
    """使用 yfinance 抓取個股新聞"""
    try:
        t = yf.Ticker(ticker_symbol)
        news_list = t.news
        if not news_list:
            return 0
        
        cur = conn.cursor()
        count = 0
        
        for item in news_list:
            content = item.get('content', {})
            title = content.get('title', '')
            link = content.get('canonicalUrl', {}).get('url', '')
            pub_date = content.get('pubDate', '')[:10] if content.get('pubDate') else ''
            provider = content.get('provider', {}).get('displayName', 'Yahoo Finance')
            
            if not title:
                continue
            
            # 情緒分析
            text = title
            sentiment = simple_sentiment(text)
            
            cur.execute('''
                INSERT OR IGNORE INTO news (date, source, title, content, sentiment, related_stocks, url, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pub_date, provider, title, '', sentiment, ticker_symbol, link, datetime.now().strftime('%Y-%m-%d %H:%M')))
            
            if cur.rowcount > 0:
                count += 1
        
        conn.commit()
        return count
    except Exception as e:
        print(f'  Error fetching {ticker_symbol}: {e}')
        return 0

def fetch_benzinga_news(conn):
    """抓取 Benzinga 美股新聞"""
    try:
        url = 'https://www.benzinga.com/news/stock-market'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            return 0
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = soup.find_all('article')[:20]  # 取前20篇
        
        cur = conn.cursor()
        count = 0
        
        for art in articles:
            title_elem = art.find('h3') or art.find('h2') or art.find('a')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            link_elem = art.find('a', href=True)
            link = link_elem['href'] if link_elem else ''
            
            if title:
                sentiment = simple_sentiment(title)
                cur.execute('''
                    INSERT OR IGNORE INTO news (date, source, title, content, sentiment, related_stocks, url, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (datetime.now().strftime('%Y-%m-%d'), 'Benzinga', title, '', sentiment, '', link, datetime.now().strftime('%Y-%m-%d %H:%M')))
                
                if cur.rowcount > 0:
                    count += 1
        
        conn.commit()
        return count
    except Exception as e:
        print(f'  Benzinga error: {e}')
        return 0

def main():
    print('=' * 60)
    print('US STOCK NEWS CRAWLER')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    print()
    
    conn = init_db()
    print(f'Database: {DB_PATH}')
    print()
    
    # 用 yfinance 抓主要股票新聞
    tickers = ['SPY', 'QQQ', 'NVDA', 'META', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'TSLA', 'AMD']
    
    print('[1] Fetching yfinance news...')
    total = 0
    for sym in tickers:
        count = fetch_yfinance_news(sym, conn)
        if count > 0:
            print(f'  {sym}: {count} news')
            total += count
    
    print(f'  Total yfinance: {total} news')
    
    print()
    print('[2] Fetching Benzinga news...')
    count = fetch_benzinga_news(conn)
    print(f'  Benzinga: {count} news')
    
    print()
    print('[3] Summary...')
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM news')
    total = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(sentiment) FROM news WHERE fetched_at >= datetime('now', '-24 hours')")
    avg_sentiment = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM news WHERE sentiment > 0.2 AND fetched_at >= datetime('now', '-24 hours')")
    pos_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM news WHERE sentiment < -0.2 AND fetched_at >= datetime('now', '-24 hours')")
    neg_count = cur.fetchone()[0]
    
    print(f'  Total news in DB: {total}')
    print(f'  24h avg sentiment: {avg_sentiment:+.2f}')
    print(f'  Positive news (24h): {pos_count}')
    print(f'  Negative news (24h): {neg_count}')
    
    print()
    print('[4] Recent news sample...')
    cur.execute('''
        SELECT date, source, sentiment, title FROM news 
        ORDER BY fetched_at DESC LIMIT 10
    ''')
    
    print()
    print(f'{"Date":<12} {"Source":<12} {"Sent":>6} {"Title":<40}')
    print('-' * 72)
    for row in cur.fetchall():
        date, source, sent, title = row
        sent_str = f'{sent:+.2f}' if sent else '0.00'
        print(f'{str(date)[:10]:<12} {str(source)[:12]:<12} {sent_str:>6} {str(title)[:40]:<40}')
    
    conn.close()
    print()
    print('=' * 60)
    print('DONE')

if __name__ == '__main__':
    main()