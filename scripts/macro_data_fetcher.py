# -*- coding: utf-8 -*-
"""
Macro Data Fetcher — Tina 宏觀數據真實抓取
==========================================
功能：
1. 搜尋地緣政治新聞（Tavily）
2. 抓取總經數據（yfinance：美債殖利率、美元指數、VIX）
3. 搜尋市場趨勢主題
4. 搜尋台美股重要財報
5. 輸出結構化 JSON

用法：
  python macro_data_fetcher.py --type morning   # 晨間 Macro
  python macro_data_fetcher.py --type afternoon  # 盤後 Macro
"""

import sys, json, os
from datetime import datetime, date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
OUTPUT_DIR = BASE_DIR / 'reports' / 'macro'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_market_data():
    """yfinance 即時市場數據"""
    import yfinance as yf
    data = {}
    try:
        # 美國宏觀指標
        tickers = {
            'US10Y': 'TLT',      # 20年期美債 ETF（代理殖利率）
            'DXY': 'UUP',         # 美元指數
            'VIX': '^VIX',        # VIX 恐慌指數
            'DOW': '^DJI',        # 道瓊
            'NASDAQ': '^IXIC',    # 納斯達克
            'SP500': '^GSPC',     # S&P 500
            'TWII': '^TWII',      # 台灣加權
        }
        for name, ticker_id in tickers.items():
            try:
                t = yf.Ticker(ticker_id)
                hist = t.history(period='2d')
                if len(hist) >= 1:
                    row = hist.iloc[-1]
                    prev = hist.iloc[-2] if len(hist) >= 2 else row
                    change = (row['Close'] - prev['Close']) / prev['Close'] * 100
                    data[name] = {
                        'price': round(float(row['Close']), 2),
                        'change_pct': round(float(change), 2)
                    }
            except Exception:
                data[name] = {'price': None, 'change_pct': None}
    except Exception as e:
        data['error'] = str(e)
    return data

def search_geopolitical(report_type):
    """搜尋地緣政治新聞"""
    queries = {
        'morning': [
            'US China trade war tariff latest news 2026',
            'Taiwan Strait military tension news 2026',
            'Ukraine Russia war latest update 2026',
        ],
        'afternoon': [
            'US China negotiation update today 2026',
            'Fed interest rate decision today 2026',
            'global geopolitical risk market impact 2026',
        ]
    }
    return queries.get(report_type, queries['morning'])

def search_economic(report_type):
    """搜尋總經數據"""
    queries = {
        'morning': [
            'CPI inflation US consumer price index latest data 2026',
            'Federal Reserve Jerome Powell speech latest 2026',
            'US Treasury yield curve latest news 2026',
        ],
        'afternoon': [
            'US economic data release today May 2026',
            'Fed minutes FOMC statement latest 2026',
            'dollar index DXY latest trend 2026',
        ]
    }
    return queries.get(report_type, queries['morning'])

def search_trends(report_type):
    """搜尋市場趨勢主題"""
    queries = {
        'morning': [
            'AI artificial intelligence semiconductor market trend 2026',
            'US stock market sector rotation May 2026',
            'Nvidia TSMC supply chain latest news 2026',
        ],
        'afternoon': [
            'stock market rally latest momentum 2026',
            'tech sector performance today 2026',
            'hot stocks trend today May 2026',
        ]
    }
    return queries.get(report_type, queries['morning'])

def search_earnings(report_type):
    """搜尋台美股財報"""
    queries = {
        'morning': [
            'Taiwan semiconductor earnings outlook 2026',
            'US tech company earnings season May 2026',
        ],
        'afternoon': [
            'TSMC earnings results May 2026',
            'Apple Microsoft Google earnings report May 2026',
            'Taiwan stock earnings surprises today 2026',
        ]
    }
    return queries.get(report_type, queries['morning'])

def build_macro_json(report_type, market_data, geo_results, econ_results, trend_results, earnings_results):
    """建構 Macro JSON 結構"""
    today = datetime.now().strftime('%Y-%m-%d')
    date_id = datetime.now().strftime('%Y%m%d')
    json_type = f'macro_{report_type}'
    
    # 地緣政治摘要
    geo_summary = '; '.join([r.get('title', '')[:80] for r in geo_results[:3] if r.get('title')]) if geo_results else ''
    geo_confidence = 0.65 if geo_summary else 0.3
    
    # 總經摘要
    econ_summary = '; '.join([r.get('title', '')[:80] for r in econ_results[:3] if r.get('title')]) if econ_results else ''
    econ_confidence = 0.7 if econ_summary else 0.3
    
    # 趨勢摘要
    trend_summary = '; '.join([r.get('title', '')[:80] for r in trend_results[:3] if r.get('title')]) if trend_results else ''
    trend_confidence = 0.7 if trend_summary else 0.3
    
    # 財報摘要
    earnings_summary = [r.get('title', '')[:100] for r in earnings_results[:3] if r.get('title')] if earnings_results else []
    earnings_confidence = 0.6 if earnings_summary else 0.3
    
    json_data = {
        'date': today,
        'type': json_type,
        'report_timestamp': datetime.now().isoformat(),
        'geopolitical': {
            'summary': geo_summary,
            'items': [
                {'title': r.get('title', ''), 'source': r.get('source', '')} 
                for r in geo_results[:5] if r.get('title')
            ],
            'confidence': geo_confidence,
            'actual': None
        },
        'economic': {
            'summary': econ_summary,
            'items': [
                {'title': r.get('title', ''), 'source': r.get('source', '')}
                for r in econ_results[:5] if r.get('title')
            ],
            'confidence': econ_confidence,
            'actual': None
        },
        'market_data': market_data,
        'trend_theme': {
            'summary': trend_summary,
            'items': [
                {'title': r.get('title', ''), 'source': r.get('source', '')}
                for r in trend_results[:5] if r.get('title')
            ],
            'confidence': trend_confidence
        },
        'earnings': {
            'highlights': earnings_summary,
            'items': [
                {'title': r.get('title', ''), 'source': r.get('source', '')}
                for r in earnings_results[:5] if r.get('title')
            ],
            'confidence': earnings_confidence
        }
    }
    
    if report_type == 'morning':
        json_data['taiwan_impact'] = {
            'forecast': None,
            'confidence': 0.5
        }
    else:
        json_data['taiwan_tomorrow'] = {
            'forecast': None,
            'confidence': 0.5
        }
    
    return json_data

def save_json(json_data, report_type):
    """寫入 JSON 檔"""
    date_id = datetime.now().strftime('%Y%m%d')
    filename = f'{date_id}_{report_type}.json'
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    return filepath

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', '--type', dest='type', default='morning',
                        choices=['morning', 'afternoon'],
                        help='morning or afternoon report')
    args = parser.parse_args()
    report_type = args.type
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'=== Macro Data Fetcher ===')
    print(f'Time: {today}')
    print(f'Type: {report_type}')
    print(f'Fetching market data...')
    
    # Step 1: yfinance 市場數據
    market_data = get_market_data()
    print(f'  Market data: {json.dumps(market_data, ensure_ascii=False)[:200]}')
    
    # Step 2-5: Tavily 搜尋（占位，實際由 caller 的 agentTurn 處理）
    # 這裡只標記需要搜尋的 queries
    geo_queries = search_geopolitical(report_type)
    econ_queries = search_economic(report_type)
    trend_queries = search_trends(report_type)
    earnings_queries = search_earnings(report_type)
    
    print(f'  Geopolitical queries: {len(geo_queries)}')
    print(f'  Economic queries: {len(econ_queries)}')
    print(f'  Trend queries: {len(trend_queries)}')
    print(f'  Earnings queries: {len(earnings_queries)}')
    
    # 初始 JSON（搜尋結果稍後由 agent 加入）
    initial_json = build_macro_json(
        report_type, market_data,
        [], [], [], []  # 搜尋結果由 macro jobs 補上
    )
    
    filepath = save_json(initial_json, report_type)
    print(f'JSON written: {filepath}')
    print(f'DONE')

if __name__ == '__main__':
    main()
