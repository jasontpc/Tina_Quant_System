# -*- coding: utf-8 -*-
"""
CN News Fetcher — 中國新聞
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category

def fetch_cn_news(date_str):
    """抓取中國財經新聞"""
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        url = 'https://finance.sina.com.cn/'
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('.news-link')[:15]:
            headline = item.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue
            sent, lvl = calc_sentiment(headline)
            cats = detect_category(headline)
            link = item.get('href', '')
            articles.append({
                'country': 'CN',
                'date': date_str,
                'datetime': date_str + ' 09:00:00',
                'category': cats[0] if cats else 'general',
                'headline': headline,
                'content': '',
                'sentiment': sent,
                'sentiment_score': lvl,
                'source': 'Sina Finance',
                'url': link,
                'related_stocks': '',
            })
    except Exception as e:
        print(f"CN news error: {e}")
    return articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_cn_news(today)
    print(f"Fetched {len(arts)} CN articles")