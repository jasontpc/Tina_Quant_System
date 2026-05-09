# -*- coding: utf-8 -*-
"""
News Trends Report Generator — 每日新聞趨勢分析報告
"""
import sqlite3
import json
import os
import sys
from datetime import datetime

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = os.path.join(DATA_DIR, 'news_trends.db')
REPORT_DIR = os.path.join(DATA_DIR, 'news_reports')

os.makedirs(REPORT_DIR, exist_ok=True)

COUNTRY_NAMES = {
    'TW': '[TW] 台灣',
    'US': '[US] 美國',
    'JP': '[JP] 日本',
    'KR': '[KR] 韓國',
    'CN': '[CN] 中國',
    'EU': '[EU] 歐洲',
}

COUNTRY_FLAGS = {
    'TW': '台灣', 'US': '美國', 'JP': '日本',
    'KR': '韓國', 'CN': '中國', 'EU': '歐洲',
}

SENTIMENT_LABELS = {
    'bullish': '[BULL] 多頭',
    'bearish': '[BEAR] 空頭',
    'neutral': '[NEUT] 中立',
}

def get_db():
    return sqlite3.connect(DB_PATH)

def get_sentiment_emoji(sentiment):
    if sentiment >= 0.3:
        return '[+]'  # 綠
    elif sentiment >= 0.1:
        return '[+~]'  # 黃綠
    elif sentiment <= -0.3:
        return '[-]'  # 紅
    elif sentiment <= -0.1:
        return '[-~]'  # 橙
    else:
        return '[=]'  # 中立

def generate_report(date_str=None, days=7):
    """產生每日新聞趨勢報告"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    countries = ['TW', 'US', 'JP', 'KR', 'CN', 'EU']
    
    report_lines = []
    overall_sentiment = []
    
    print(f"[NEWS] Trends Report — {date_str}")
    print("=" * 60)
    
    for country in countries:
        cur = conn.cursor()
        cur.execute('''
            SELECT date, avg_sentiment, article_count, trend_direction, hot_categories, hot_stocks
            FROM daily_trends
            WHERE country = ? AND date <= ?
            ORDER BY date DESC
            LIMIT ?
        ''', (country, date_str, days))
        rows = cur.fetchall()
        
        if not rows:
            print(f"\n{COUNTRY_NAMES[country]} — 暫無資料")
            continue
        
        sentiments = [r[1] for r in rows if r[1] is not None]
        avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0
        total_articles = sum(r[2] for r in rows if r[2])
        overall_sentiment.append((country, avg_sent, total_articles))
        
        latest = rows[0]
        direction = latest[3] or 'neutral'
        hot_cats = json.loads(latest[4]) if latest[4] else []
        
        emoji = SENTIMENT_LABELS.get(direction, '[NEUT]')
        sent_emoji = get_sentiment_emoji(avg_sent)
        cname = COUNTRY_FLAGS.get(country, country)
        
        print(f"\n{cname} {emoji}")
        print(f"  情緒: {avg_sent:+.3f} {sent_emoji} ({total_articles}篇)")
        print(f"  類別: {', '.join(hot_cats[:4]) if hot_cats else 'N/A'}")
        
        if len(rows) >= 2:
            prev = rows[1][1] or 0
            delta = avg_sent - prev
            arrow = '▲' if delta > 0.02 else '▼' if delta < -0.02 else '─'
            print(f"  趨勢: {arrow} {delta:+.3f}")
    
    # 情緒排名
    print(f"\n{'=' * 60}")
    print("Rank 各國市場情緒排名：")
    sorted_countries = sorted(overall_sentiment, key=lambda x: x[1], reverse=True)
    
    lines = [f'[NEWS] 新聞趨勢報告 — {date_str}', '']
    
    for i, (c, s, cnt) in enumerate(sorted_countries, 1):
        sent_emoji = get_sentiment_emoji(s)
        flag = COUNTRY_FLAGS.get(c, c)
        
        bar_len = int(abs(s) * 12)
        bar = '+' * bar_len if bar_len > 0 else ''
        direction_mark = '+' if s > 0 else '' if s < 0 else ''
        
        line = f"{i}. {flag} {sent_emoji} {s:+.3f} {bar} ({cnt}篇)"
        print(f"  {line}")
        lines.append(line)
    
    # 報告檔案
    report_path = os.path.join(REPORT_DIR, f'news_trends_{date_str}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n[OK] Report saved: {report_path}")
    conn.close()
    
    return '\n'.join(lines)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', '-d', default=None)
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    
    date_str = args.date or datetime.now().strftime('%Y-%m-%d')
    generate_report(date_str, days=args.days)