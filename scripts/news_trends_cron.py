# -*- coding: utf-8 -*-
"""
News Trends Cron Driver v2 — 獨立執行版
每日 08:00 / 14:00 / 20:00 執行
"""
import os
import sys
import sqlite3
import json
from datetime import datetime

# Setup path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = os.path.join(DATA_DIR, 'news_trends.db')
sys.path.insert(0, SCRIPT_DIR)

# Import sentiment analyzer from local
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'news_trends'))
from news_trends.sentiment_analyzer import calc_sentiment, detect_category

# Import country fetchers
from news_trends.news_tw import fetch_tw_news
from news_trends.news_us import fetch_us_news
from news_trends.news_jp import fetch_jp_news
from news_trends.news_kr import fetch_kr_news
from news_trends.news_cn import fetch_cn_news
from news_trends.news_eu import fetch_eu_news

COUNTRY_FETCHERS = {
    'TW': fetch_tw_news,
    'US': fetch_us_news,
    'JP': fetch_jp_news,
    'KR': fetch_kr_news,
    'CN': fetch_cn_news,
    'EU': fetch_eu_news,
}

def get_db():
    return sqlite3.connect(DB_PATH)

def upsert_article(conn, article):
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO news_articles 
        (country, date, datetime, category, headline, content, sentiment, sentiment_score, source, url, related_stocks, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        article['country'],
        article.get('date', datetime.now().strftime('%Y-%m-%d')),
        article.get('datetime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        article.get('category', 'general'),
        article['headline'],
        article.get('content', ''),
        article.get('sentiment', 0),
        article.get('sentiment_score', 1),
        article.get('source', 'unknown'),
        article.get('url', ''),
        article.get('related_stocks', ''),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    ))

def update_daily_trends(conn, country, date):
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) as cnt, AVG(sentiment) as avg_sent
        FROM news_articles
        WHERE country = ? AND date = ?
    ''', (country, date))
    row = cur.fetchone()
    
    if row and row[0] > 0:
        cnt = row[0]
        avg_sent = row[1] or 0
        
        cur.execute('''
            SELECT category, COUNT(*) as cnt
            FROM news_articles
            WHERE country = ? AND date = ?
            GROUP BY category ORDER BY cnt DESC LIMIT 5
        ''', (country, date))
        hot_cats = [r[0] for r in cur.fetchall()]
        
        cur.execute('''
            SELECT related_stocks, COUNT(*) as cnt
            FROM news_articles
            WHERE country = ? AND date = ? AND related_stocks != ''
            GROUP BY related_stocks ORDER BY cnt DESC LIMIT 5
        ''', (country, date))
        hot_stocks = [r[0] for r in cur.fetchall()]
        
        direction = 'bullish' if avg_sent > 0.15 else 'bearish' if avg_sent < -0.15 else 'neutral'
        
        cur.execute('''
            INSERT OR REPLACE INTO daily_trends 
            (country, date, avg_sentiment, article_count, hot_categories, hot_stocks, trend_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (country, date, round(avg_sent, 3), cnt, json.dumps(hot_cats), json.dumps(hot_stocks), direction))
        
        return {'sentiment': round(avg_sent, 3), 'count': cnt, 'direction': direction}
    return None

def run(countries=None, target_date=None):
    if not os.path.exists(DB_PATH):
        print("[ERROR] DB not found. Run init_news_trends_db.py first.")
        return
    
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    if countries is None:
        countries = list(COUNTRY_FETCHERS.keys())
    
    conn = get_db()
    results = {}
    
    print(f"[NEWS] Trends Aggregator — {target_date}")
    print("=" * 50)
    
    for country in countries:
        fetcher = COUNTRY_FETCHERS.get(country)
        if not fetcher:
            continue
        
        print(f"[{country}] Fetching...")
        try:
            articles = fetcher(target_date)
            inserted = 0
            for art in articles:
                upsert_article(conn, art)
                inserted += 1
            conn.commit()
            
            trend = update_daily_trends(conn, country, target_date)
            results[country] = {'fetched': inserted, 'trend': trend}
            
            t = trend or {}
            emoji = '[UP]' if t.get('direction') == 'bullish' else '[DOWN]' if t.get('direction') == 'bearish' else '[--]'
            print(f"  [OK] {inserted} articles, sentiment={t.get('sentiment', '?')} {emoji}")
        except Exception as e:
            results[country] = {'error': str(e)}
            print(f"  [ERROR] {e}")
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("Summary:")
    total = 0
    for c, r in results.items():
        if 'error' in r:
            print(f"  {c}: ERROR {r['error']}")
        else:
            t = r.get('trend') or {}
            print(f"  {c}: sent={t.get('sentiment', '?')} ({r.get('fetched', 0)} articles)")
            total += r.get('fetched', 0)
    
    print(f"\n[OK] Total {total} articles processed")
    return results

if __name__ == '__main__':
    countries_env = os.environ.get('NEWS_COUNTRIES', 'TW,US,JP,KR,CN,EU')
    date_env = os.environ.get('NEWS_DATE', datetime.now().strftime('%Y-%m-%d'))
    
    country_list = [c.strip() for c in countries_env.split(',')]
    run(countries=country_list, target_date=date_env)