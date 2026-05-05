# -*- coding: utf-8 -*-
"""
Tina 每日趨勢掃描
=================
Tavily AI 搜尋台股/美股宏觀趨勢，產出摘要報告
"""
import requests
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

TAVILY_KEY = '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'
URL = 'https://api.tavily.com/search'

QUERIES = [
    ('台股 分析 2026-05', '🌐 台股宏觀'),
    ('Taiwan stock market outlook May 2026', '🌐 TW Market'),
    ('AI semiconductor stocks outlook May 2026', '🤖 AI 半導體'),
    ('TSMC NVDA INTC MU stock outlook May 2026', '💎 晶片巨頭'),
    ('optical fiber photonics Taiwan May 2026', '🌈 光通訊'),
    ('乾淨能源 風電 太陽能 2026', '⚡ 綠能'),
]


def search(query):
    try:
        r = requests.post(URL, json={
            'api_key': TAVILY_KEY,
            'query': query,
            'max_results': 5
        }, timeout=15)
        d = r.json()
        return d.get('results', [])
    except Exception as e:
        return []


def main():
    print("=" * 65)
    print("  Tina 每日趨勢掃描")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    for query, label in QUERIES:
        results = search(query)
        if results:
            print(f"[{label}] {query}")
            for item in results[:3]:
                title = item.get('title', '')[:65]
                score = item.get('score', 0)
                print(f"  {score:.2f} {title}")
            print()

    print("=" * 65)
    print("[DONE]")


if __name__ == '__main__':
    main()
