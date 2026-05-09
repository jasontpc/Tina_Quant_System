# -*- coding: utf-8 -*-
"""
EU News Fetcher — 歐洲新聞
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category

def fetch_eu_news(date_str):
    """抓取歐洲財經新聞"""
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        # Euronext 主要市場新聞
        url = 'https://www.euronext.com/en/news'
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('article h3')[:10]:
            headline = item.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue
            sent, lvl = calc_sentiment(headline)
            cats = detect_category(headline)
            articles.append({
                'country': 'EU',
                'date': date_str,
                'datetime': date_str + ' 08:00:00',
                'category': cats[0] if cats else 'general',
                'headline': headline,
                'content': '',
                'sentiment': sent,
                'sentiment_score': lvl,
                'source': 'Euronext',
                'url': '',
                'related_stocks': '',
            })
    except Exception as e:
        print(f"EU news error: {e}")
    return articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_eu_news(today)
    print(f"Fetched {len(arts)} EU articles")