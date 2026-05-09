# -*- coding: utf-8 -*-
"""
News Aggregator — 各國新聞彙整與每日更新
每日上午 08:00 執行（08:00 TW/14:00 US/20:00 EU）
"""
import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from sentiment_analyzer import calc_sentiment

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = os.path.join(DATA_DIR, 'news_trends.db')
SCRIPT_DIR = os.path.dirname(__file__)

# ---------- Crawler Modules (各國爬蟲) ----------
from news_tw import fetch_tw_news
from news_us import fetch_us_news
from news_jp import fetch_jp_news
from news_kr import fetch_kr_news
from news_cn import fetch_cn_news
from news_eu import fetch_eu_news

COUNTRY_FETCHERS = {
    'TW': fetch_tw_news,
    'US': fetch_us_news,
    'JP': fetch_jp_news,
    'KR': fetch_kr_news,
    'CN': fetch_cn_news,
    'EU': fetch_eu_news,
}

def get_db_connection():
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
    """根據已抓取的新聞，更新 daily_trends"""
    cur = conn.cursor()
    
    # 取得當日文章統計
    cur.execute('''
        SELECT 
            COUNT(*) as cnt,
            AVG(sentiment) as avg_sent
        FROM news_articles
        WHERE country = ? AND date = ?
    ''', (country, date))
    row = cur.fetchone()
    
    if row and row[0] > 0:
        cnt = row[0]
        avg_sent = row[1] or 0
        
        # 熱門類別
        cur.execute('''
            SELECT category, COUNT(*) as cnt
            FROM news_articles
            WHERE country = ? AND date = ?
            GROUP BY category
            ORDER BY cnt DESC
            LIMIT 5
        ''', (country, date))
        hot_cats = [r[0] for r in cur.fetchall()]
        
        # 熱門股票
        cur.execute('''
            SELECT related_stocks, COUNT(*) as cnt
            FROM news_articles
            WHERE country = ? AND date = ? AND related_stocks != ''
            GROUP BY related_stocks
            ORDER BY cnt DESC
            LIMIT 5
        ''', (country, date))
        hot_stocks = [r[0] for r in cur.fetchall()]
        
        # 趨勢方向
        if avg_sent > 0.15:
            direction = 'bullish'
        elif avg_sent < -0.15:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        cur.execute('''
            INSERT OR REPLACE INTO daily_trends 
            (country, date, avg_sentiment, article_count, hot_categories, hot_stocks, trend_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (country, date, round(avg_sent, 3), cnt, json.dumps(hot_cats), json.dumps(hot_stocks), direction))
        
        return {'sentiment': round(avg_sent, 3), 'count': cnt, 'direction': direction}
    return None

def run_aggregate(countries=None, target_date=None):
    """主要彙整流程"""
    if not os.path.exists(DB_PATH):
        print("❌ DB not found. Run init_news_trends_db.py first.")
        return
    
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    if countries is None:
        countries = list(COUNTRY_FETCHERS.keys())
    
    conn = get_db_connection()
    results = {}
    
    print(f"📰 News Trends Aggregator — {target_date}")
    print("=" * 50)
    
    for country in countries:
        fetcher = COUNTRY_FETCHERS.get(country)
        if not fetcher:
            continue
        
        print(f"\n🌏 {country}: Fetching...")
        try:
            articles = fetcher(target_date)
            inserted = 0
            for art in articles:
                upsert_article(conn, art)
                inserted += 1
            conn.commit()
            
            trend = update_daily_trends(conn, country, target_date)
            results[country] = {
                'fetched': inserted,
                'trend': trend
            }
            print(f"  ✅ {inserted} articles, sentiment={trend['sentiment'] if trend else 'N/A'}")
        except Exception as e:
            results[country] = {'error': str(e)}
            print(f"  ❌ Error: {e}")
    
    conn.close()
    
    # 產出摘要
    print("\n" + "=" * 50)
    print("📊 Daily Summary:")
    for c, r in results.items():
        if 'error' in r:
            print(f"  {c}: ❌ {r['error']}")
        else:
            t = r.get('trend', {})
            emoji = '📈' if t.get('direction') == 'bullish' else '📉' if t.get('direction') == 'bearish' else '➡️'
            print(f"  {c}: {emoji} sent={t.get('sentiment', '?')} ({r.get('fetched', 0)} articles)")
    
    return results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--countries', '-c', default='TW,US,JP,KR,CN,EU')
    parser.add_argument('--date', '-d', default=None)
    args = parser.parse_args()
    
    countries = args.countries.split(',') if args.countries else None
    date = args.date or datetime.now().strftime('%Y-%m-%d')
    
    run_aggregate(countries=countries, target_date=date)