# -*- coding: utf-8 -*-
"""
JP News Fetcher — 日本新聞
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category

def fetch_jp_news(date_str):
    """抓取日本新聞"""
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ja-JP,ja;q=0.9',
        }
        # 簡單先用 Yahoo Finance JP
        url = 'https://finance.yahoo.co.jp/news'
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('._3g42')[:15]:
            headline = item.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue
            sent, lvl = calc_sentiment(headline)
            cats = detect_category(headline)
            articles.append({
                'country': 'JP',
                'date': date_str,
                'datetime': date_str + ' 08:00:00',
                'category': cats[0] if cats else 'general',
                'headline': headline,
                'content': '',
                'sentiment': sent,
                'sentiment_score': lvl,
                'source': 'Yahoo Finance JP',
                'url': '',
                'related_stocks': '',
            })
    except Exception as e:
        print(f"JP news error: {e}")
    return articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_jp_news(today)
    print(f"Fetched {len(arts)} JP articles")