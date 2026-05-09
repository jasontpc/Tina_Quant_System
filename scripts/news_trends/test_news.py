# -*- coding: utf-8 -*-
import yfinance as yf
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

tickers = ['2330.TW', 'AAPL', 'NVDA']
for sym in tickers:
    t = yf.Ticker(sym)
    news = getattr(t, 'news', []) or []
    print(f"\n{sym}: {len(news)} news items")
    for item in news[:2]:
        content = item.get('content', {})
        if isinstance(content, dict):
            title = content.get('title', '') or ''
            summary = content.get('summary', '') or ''
        else:
            title = str(content)[:60]
            summary = ''
        print(f"  Title: {title[:60]}")
        print(f"  Summary: {str(summary)[:80]}")