# -*- coding: utf-8 -*-
"""
TW News Fetcher — 台灣新聞 v2
"""
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sentiment_analyzer import calc_sentiment, detect_category
import sys
sys.stdout.reconfigure(encoding='utf-8')

TW_TICKERS = ['2330.TW', '2454.TW', '2317.TW', '2382.TW', '3034.TW', '6511.TW', '3037.TW']

def fetch_yf_news(date_str):
    """使用 yfinance 抓取台股相關新聞"""
    articles = []
    for ticker in TW_TICKERS:
        try:
            t = yf.Ticker(ticker)
            news_list = getattr(t, 'news', []) or []
            for item in news_list[:5]:
                # 解析 content 結構
                content = item.get('content', {})
                if isinstance(content, dict):
                    headline = content.get('title', '') or content.get('headline', '')
                    summary = content.get('summary', '') or ''
                else:
                    headline = ''
                    summary = ''
                
                if not headline:
                    continue
                
                # 時間戳
                pub = item.get('providerPublishTime') or 0
                item_date = datetime.fromtimestamp(pub).strftime('%Y-%m-%d') if pub else date_str
                item_dt = datetime.fromtimestamp(pub).strftime('%Y-%m-%d %H:%M:%S') if pub else f'{date_str} 12:00:00'
                
                sent, lvl = calc_sentiment(headline, summary)
                cats = detect_category(headline, summary)
                related = ticker.replace('.TW', '')
                
                articles.append({
                    'country': 'TW',
                    'date': item_date,
                    'datetime': item_dt,
                    'category': cats[0] if cats else 'general',
                    'headline': headline,
                    'content': str(summary)[:500],
                    'sentiment': sent,
                    'sentiment_score': lvl,
                    'source': 'yfinance',
                    'url': item.get('clickThroughUrl', {}).get('url', '') if isinstance(item.get('clickThroughUrl'), dict) else '',
                    'related_stocks': related,
                })
        except Exception as e:
            pass
    return articles

def fetch_cnyes(date_str):
    """抓取鉅亨網新聞"""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = 'https://news.cnyes.com/news/cat/tw_market'
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('._1ZFR')[:15]:
            headline = item.get_text(strip=True)
            if not headline or len(headline) < 5:
                continue
            sent, lvl = calc_sentiment(headline)
            cats = detect_category(headline)
            articles.append({
                'country': 'TW',
                'date': date_str,
                'datetime': f'{date_str} 12:00:00',
                'category': cats[0] if cats else 'general',
                'headline': headline,
                'content': '',
                'sentiment': sent,
                'sentiment_score': lvl,
                'source': 'cnyes',
                'url': '',
                'related_stocks': '',
            })
    except Exception as e:
        print(f"cnyes fetch error: {e}")
    return articles

def fetch_tw_news(date_str):
    """主程式：彙整所有 TW 來源"""
    all_articles = fetch_yf_news(date_str)
    # cnyes 需要在有網路環境測試
    return all_articles

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    arts = fetch_tw_news(today)
    print(f"Fetched {len(arts)} TW articles")
    for a in arts[:5]:
        print(f"  [{a['sentiment']:+.2f} L{a['sentiment_score']}] {a['headline'][:50]}...")
        print(f"    => category: {a['category']}")