# -*- coding: utf-8 -*-
"""
News Trends Database Initializer
初始化新聞趨勢資料庫
"""
import sqlite3
import os
from datetime import datetime

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = os.path.join(DATA_DIR, 'news_trends.db')

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # News Articles Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            date TEXT,
            datetime TEXT,
            category TEXT,
            headline TEXT,
            content TEXT,
            sentiment REAL DEFAULT 0,
            sentiment_score INTEGER DEFAULT 1,
            source TEXT,
            url TEXT,
            related_stocks TEXT,
            fetched_at TEXT,
            UNIQUE(country, headline, date)
        )
    ''')

    # Daily Trends Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            date TEXT NOT NULL,
            avg_sentiment REAL DEFAULT 0,
            article_count INTEGER DEFAULT 0,
            hot_categories TEXT,
            hot_stocks TEXT,
            trend_direction TEXT DEFAULT 'neutral',
            UNIQUE(country, date)
        )
    ''')

    # Sources Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            priority INTEGER DEFAULT 2,
            last_fetch TEXT,
            UNIQUE(country, source_name)
        )
    ''')

    # Indexes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_news_country_date ON news_articles(country, date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_trends_country ON daily_trends(country, date)')

    conn.commit()
    conn.close()
    print(f"[OK] News Trends DB initialized: {DB_PATH}")

def seed_sources():
    """初始化新聞來源"""
    sources = [
        # TW
        ('TW', 'yfinance', 'https://finance.yahoo.com', 1),
        ('TW', 'UDN', 'https://udn.com', 2),
        ('TW', 'cnyes', 'https://cnyes.com', 2),
        # US
        ('US', 'yfinance', 'https://finance.yahoo.com', 1),
        ('US', 'Benzinga', 'https://benzinga.com', 2),
        ('US', 'Reuters', 'https://reuters.com', 2),
        # JP
        ('JP', 'Yahoo Finance JP', 'https://finance.yahoo.co.jp', 1),
        ('JP', 'Nikkei', 'https://nikkei.com', 2),
        # KR
        ('KR', 'Naver Finance', 'https://finance.naver.com', 1),
        ('KR', 'Yonhap', 'https://yonhapnews.co.kr', 2),
        # CN
        ('CN', 'Sina Finance', 'https://finance.sina.com.cn', 1),
        ('CN', 'Tencent Finance', 'https://finance.qq.com', 2),
        # EU
        ('EU', 'Yahoo Finance UK', 'https://uk.finance.yahoo.com', 1),
        ('EU', 'Euronext', 'https://euronext.com', 2),
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany('''
        INSERT OR IGNORE INTO sources (country, source_name, source_url, priority)
        VALUES (?, ?, ?, ?)
    ''', sources)
    conn.commit()
    conn.close()
    print(f"[OK] Seeded {len(sources)} news sources")

if __name__ == '__main__':
    init_db()
    seed_sources()
    print("[OK] News Trends Database ready!")