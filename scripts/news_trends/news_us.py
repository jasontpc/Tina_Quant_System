# -*- coding: utf-8 -*-
"""
US News Fetcher — 美國新聞 v2
"""
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category
import sys
sys.stdout.reconfigure(encoding='utf-8')

US_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'QCOM']

def fetch_yf_news(date_str):
    """使用 yfinance 抓取美股新聞"""
    articles = []
    for ticker in US_TICKERS:
        try:
            t = yf.Ticker(ticker)
            news_list = getattr(t, 'news', []) or []
            for item in news_list[:5]:
                content = item.get('content', {})
                if isinstance(content, dict):
                    headline = content.get('title', '') or content.get('headline', '')
                    summary = content.get('summary', '') or ''
                else:
                    headline = ''
                    summary = ''
                
                if not headline:
                    continue
                
                pub = item.get('providerPublishTime') or 0
                item_date = datetime.fromtimestamp(pub).strftime('%Y-%m-%d') if pub else date_str
                item_dt = datetime.fromtimestamp(pub).strftime('%Y-%m-%d %H:%M:%S') if pub else f'{date_str} 09:00:00'
                
                sent, lvl = calc_sentiment(headline, summary)
                cats = detect_category(headline, summary)
                
                articles.append({
                    'country': 'US',
                    'date': item_date,
                    'datetime': item_dt,
                    'category': cats[0] if cats else 'general',
                    'headline': headline,
                    'content': str(summary)[:500],
                    'sentiment': sent,
                    'sentiment_score': lvl,
                    'source': 'yfinance',
                    'url': item.get('clickThroughUrl', {}).get('url', '') if isinstance(item.get('clickThroughUrl'), dict) else '',
                    'related_stocks': ticker,
                })
        except Exception:
            pass
    return articles

def fetch_benzinga(date_str):
    """抓取 Benzinga 新聞"""
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = 'https://www.benzinga.com/top/stocks'
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('article .title')[:15]:
            headline = item.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue
            sent, lvl = calc_sentiment(headline)
            cats = detect_category(headline)
            link = item.find('a')
            articles.append({
                'country': 'US',
                'date': date_str,
                'datetime': f'{date_str} 09:00:00',
                'category': cats[0] if cats else 'general',
                'headline': headline,
                'content': '',
                'sentiment': sent,
                'sentiment_score': lvl,
                'source': 'benzinga',
                'url': link['href'] if link and link.has_attr('href') else '',
                'related_stocks': '',
            })
    except Exception as e:
        print(f"benzinga error: {e}")
    return articles

def fetch_us_news(date_str):
    """主程式：彙整所有 US 來源"""
    all_articles = fetch_yf_news(date_str)
    return all_articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_us_news(today)
    print(f"Fetched {len(arts)} US articles")
    for a in arts[:5]:
        print(f"  [{a['sentiment']:+.2f} L{a['sentiment_score']}] {a['headline'][:50]}...")
        print(f"    => category: {a['category']}")