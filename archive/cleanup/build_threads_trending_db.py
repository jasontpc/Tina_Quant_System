# -*- coding: utf-8 -*-
"""
Threads 趨勢資料庫 — 台股/美股/關鍵字趨勢追蹤
用途：追蹤社群媒體熱門關鍵字熱度變化
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
from datetime import datetime

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = os.path.join(BASE, "data")
DB = os.path.join(DATA_DIR, "threads_trending.db")

def init_db():
    """初始化 threads 趨勢資料庫"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # 關鍵字主檔
    cur.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        category TEXT,  -- TW_STOCK, US_STOCK, TECH, ETF, MACRO, SENTIMENT
        alias TEXT,  -- 別名/相關詞
        source TEXT,  -- 資料來源: PTT, Dcard, Mobile01, NEWS, Twitter
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )''')
    
    # 趨勢記錄（每筆爬蟲的熱度分數）
    cur.execute('''CREATE TABLE IF NOT EXISTS trend_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword_id INTEGER,
        timestamp TEXT,
       热度_score INTEGER,  -- 熱度分數 0-100
        mention_count INTEGER,  -- 討論次數
        sentiment TEXT,  -- POSITIVE, NEGATIVE, NEUTRAL
        source TEXT,
        title TEXT,  -- 熱門標題摘要
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (keyword_id) REFERENCES keywords(id)
    )''')
    
    # 每日趨勢彙總
    cur.execute('''CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword_id INTEGER,
        date TEXT,
        avg_score REAL,
        max_score INTEGER,
        total_mentions INTEGER,
        sentiment_positive INTEGER,
        sentiment_negative INTEGER,
        sentiment_neutral INTEGER,
        top_titles TEXT,  -- JSON array
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (keyword_id) REFERENCES keywords(id)
    )''')
    
    conn.commit()
    conn.close()
    print(f"[OK] Threads Trending DB: {DB}")

def insert_default_keywords():
    """插入預設關鍵字"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    keywords = [
        # 台股
        ("台股", "TW_STOCK", "加權指數,TWII", "PTT,Dcard,NEWS"),
        ("台積電", "TW_STOCK", "2330,TSMC,半導體", "PTT,Dcard,NEWS,Twitter"),
        ("2330", "TW_STOCK", "台積電,TSMC", "PTT,NEWS"),
        ("聯發科", "TW_STOCK", "2454,IC設計", "PTT,Dcard"),
        ("鴻海", "TW_STOCK", "2317,富士康", "PTT,NEWS"),
        ("廣達", "TW_STOCK", "2382,AI伺服器", "PTT,Dcard"),
        ("緯穎", "TW_STOCK", "3034,AI伺服器", "PTT"),
        ("穎崴", "TW_STOCK", "3665,IC封測", "PTT"),
        ("聯發科", "TW_STOCK", "2454", "PTT"),
        ("瑞昱", "TW_STOCK", "2379", "PTT"),
        ("技嘉", "TW_STOCK", "2376,AI伺服器", "PTT"),
        
        # 金融股
        ("金控股", "TW_STOCK", "2880,2881,2882,金融", "PTT,Dcard"),
        ("國泰金", "TW_STOCK", "2881", "PTT"),
        ("富邦金", "TW_STOCK", "2881", "PTT"),
        ("中信金", "TW_STOCK", "2891", "PTT"),
        
        # ETF
        ("0050", "ETF", "元大台灣50", "PTT,Dcard,NEWS"),
        ("0056", "ETF", "元大高股息", "PTT,Dcard"),
        ("00878", "ETF", "國泰永續高息", "PTT,Dcard"),
        ("00919", "ETF", "群益台灣精選高息", "PTT,Dcard"),
        ("00713", "ETF", "元大高息低波", "PTT"),
        ("00646", "ETF", "富邦S&P500", "PTT"),
        ("00662", "ETF", "富邦NASDAQ100", "PTT"),
        
        # 美股
        ("美股", "US_STOCK", "S&P500,Nasdaq", "Twitter,NEWS,PTT"),
        ("NVDA", "US_STOCK", "輝達,AI,顯示卡", "Twitter,PTT,Dcard,NEWS"),
        ("AMD", "US_STOCK", "超微半導體", "Twitter,PTT"),
        ("TSLA", "US_STOCK", "特斯拉,電動車", "Twitter,PTT,Dcard"),
        ("AAPL", "US_STOCK", "蘋果,iPhone", "Twitter,PTT"),
        ("MSFT", "US_STOCK", "微軟,AI,雲端", "Twitter,PTT"),
        ("META", "US_STOCK", "Meta,Facebook,IG", "Twitter,PTT"),
        ("GOOGL", "US_STOCK", "Google,AI", "Twitter,PTT"),
        ("AMZN", "US_STOCK", "亞馬遜,電商,雲端", "Twitter,PTT"),
        ("SPY", "US_STOCK", "S&P500ETF", "Twitter,PTT"),
        ("QQQ", "US_STOCK", "Nasdaq100ETF", "Twitter,PTT"),
        
        # 科技趨勢
        ("AI", "TECH", "人工智慧,ChatGPT,LLM", "Twitter,PTT,Dcard,NEWS"),
        ("半導體", "TECH", "晶片,IC,先進製程", "PTT,NEWS"),
        ("電動車", "TECH", "EV,新能源車", "PTT,Dcard,NEWS"),
        ("iPhone", "TECH", "蘋果新手機", "PTT,Dcard,NEWS"),
        ("雲端", "TECH", "AWS,Azure,GCP", "PTT,NEWS"),
        ("記憶體", "TECH", "HBM,DRAM,SSD", "PTT"),
        
        # 總經/巨觀
        ("聯準會", "MACRO", "Fed,升息,降息", "Twitter,NEWS,PTT"),
        ("鮑威爾", "MACRO", "Fed主席", "NEWS,PTT"),
        ("台積電ADR", "MACRO", "TSM ADR", "Twitter,NEWS"),
        ("美債", "MACRO", "公債,殖利率", "NEWS,PTT"),
        ("原油", "MACRO", "油價,OPEC", "NEWS,PTT"),
        ("黃金", "MACRO", "Gold,避險", "NEWS,PTT"),
        
        # 市場情緒
        ("FOMO", "SENTIMENT", "錯失恐懼", "PTT,Dcard"),
        ("割韭菜", "SENTIMENT", "被坑殺", "PTT"),
        ("長期持有", "SENTIMENT", "價值投資,DCA", "PTT,Dcard"),
    ]
    
    for kw, cat, alias, source in keywords:
        cur.execute("SELECT COUNT(*) FROM keywords WHERE keyword=?", (kw,))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO keywords (keyword, category, alias, source) VALUES (?, ?, ?, ?)",
                       (kw, cat, alias, source))
    
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM keywords")
    count = cur.fetchone()[0]
    conn.close()
    print(f"[OK] Keywords: {count} default keywords inserted")

def add_custom_keyword(keyword, category, alias="", source=""):
    """動態新增關鍵字"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO keywords (keyword, category, alias, source) VALUES (?, ?, ?, ?)",
               (keyword, category, alias, source))
    conn.commit()
    conn.close()

def log_trend(keyword, score, mentions, sentiment, source, title="", url=""):
    """記錄單筆趨勢"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM keywords WHERE keyword=? AND is_active=1", (keyword,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    
    keyword_id = row[0]
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cur.execute('''INSERT INTO trend_records 
        (keyword_id, timestamp,热度_score, mention_count, sentiment, source, title, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (keyword_id, ts, score, mentions, sentiment, source, title, url))
    
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id

def get_latest_trends(category=None, limit=20):
    """取得最新趨勢"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    if category:
        cur.execute('''SELECT k.keyword, k.category, t.热度_score, t.sentiment, t.timestamp, t.title
            FROM trend_records t
            JOIN keywords k ON t.keyword_id = k.id
            WHERE k.category=? AND k.is_active=1
            ORDER BY t.timestamp DESC LIMIT ?''', (category, limit))
    else:
        cur.execute('''SELECT k.keyword, k.category, t.热度_score, t.sentiment, t.timestamp, t.title
            FROM trend_records t
            JOIN keywords k ON t.keyword_id = k.id
            WHERE k.is_active=1
            ORDER BY t.timestamp DESC LIMIT ?''', (limit,))
    
    results = []
    for row in cur.fetchall():
        results.append({
            'keyword': row[0],
            'category': row[1],
            'score': row[2],
            'sentiment': row[3],
            'timestamp': row[4],
            'title': row[5]
        })
    
    conn.close()
    return results

def get_trend_summary(keyword, days=7):
    """取得關鍵字趨勢摘要"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM keywords WHERE keyword=?", (keyword,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    
    keyword_id = row[0]
    start_date = datetime.now().strftime('%Y-%m-%d')
    
    cur.execute('''SELECT 
            AVG(热度_score), MAX(热度_score), SUM(mention_count),
            SUM(CASE WHEN sentiment='POSITIVE' THEN 1 ELSE 0 END),
            SUM(CASE WHEN sentiment='NEGATIVE' THEN 1 ELSE 0 END),
            SUM(CASE WHEN sentiment='NEUTRAL' THEN 1 ELSE 0 END)
        FROM trend_records
        WHERE keyword_id=? AND date(timestamp) >= date('now', '-? days')''',
        (keyword_id, days))
    
    row = cur.fetchone()
    conn.close()
    
    if row and row[0]:
        return {
            'keyword': keyword,
            'avg_score': round(row[0], 1),
            'max_score': row[1],
            'total_mentions': row[2],
            'positive': row[3],
            'negative': row[4],
            'neutral': row[5]
        }
    return None

# === 主程式 ===
print("=" * 60)
print("Threads 趨勢資料庫 建置")
print("=" * 60)
print()

init_db()
insert_default_keywords()

print()
print("=== 資料庫內容驗證 ===")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Show categories
cur.execute("SELECT category, COUNT(*) FROM keywords GROUP BY category")
print("\n關鍵字分類統計:")
for cat, cnt in cur.fetchall():
    print(f"  {cat}: {cnt} 關鍵字")

# Show sample keywords
cur.execute("SELECT keyword, category, alias FROM keywords LIMIT 15")
print("\n前 15 個關鍵字:")
for kw, cat, alias in cur.fetchall():
    print(f"  [{cat}] {kw} ({alias})")

conn.close()

print()
print("=== 功能說明 ===")
print("  log_trend(kw, score, mentions, sentiment, source, title)")
print("    - 記錄單筆趨勢")
print("  get_latest_trends(category=None, limit=20)")
print("    - 取得最新趨勢")
print("  get_trend_summary(keyword, days=7)")
print("    - 取得關鍵字 7 日摘要")
print("  add_custom_keyword(keyword, category, alias, source)")
print("    - 新增自訂關鍵字")

print()
print("=== 建置完成 ===")