# -*- coding: utf-8 -*-
"""
KR News Fetcher — 韓國新聞（使用 Tavily API）
"""
import os
import requests
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category

def fetch_kr_news(date_str):
    """使用 Tavily 搜尋韓國財經新聞"""
    articles = []
    api_key = os.environ.get('TAVILY_API_KEY') or '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'
    
    queries = [
        'Korea stock market news today',
        '한국 증시 뉴스 오늘',
        'KOSPI KOSDAQ news',
    ]
    
    for query in queries:
        try:
            response = requests.post(
                'https://api.tavily.com/search',
                json={'query': query, 'api_key': api_key, 'max_results': 5},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    headline = item.get('title', '')
                    content = item.get('content', '')[:300]
                    sent, lvl = calc_sentiment(headline, content)
                    cats = detect_category(headline, content)
                    articles.append({
                        'country': 'KR',
                        'date': date_str,
                        'datetime': date_str + ' 09:00:00',
                        'category': cats[0] if cats else 'general',
                        'headline': headline,
                        'content': content,
                        'sentiment': sent,
                        'sentiment_score': lvl,
                        'source': 'tavily',
                        'url': item.get('url', ''),
                        'related_stocks': '',
                    })
        except Exception as e:
            print(f"KR Tavily error: {e}")
    return articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_kr_news(today)
    print(f"Fetched {len(arts)} KR articles")
    for a in arts[:3]:
        print(f"  [{a['sentiment']:+.2f}] {a['headline'][:40]}")