# -*- coding: utf-8 -*-
"""
Fetch Institutional Data from FinMind API
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import sqlite3
import time
import json

DB = 'skills/stock-analyzer/scripts/tina_master.db'

def fetch_inst_data(symbol, start_date='2024-04-01', end_date='2026-04-22'):
    """Fetch institutional data from FinMind"""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": symbol,
        "start_date": start_date,
        "end_date": end_date,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('data'):
                return data['data']
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return []

def save_inst_data(symbol, data):
    """Save institutional data to database"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Aggregate by date and type
    daily_data = {}
    for row in data:
        date = row.get('date', '')
        name = row.get('name', '')
        buy = row.get('buy', 0) or 0
        sell = row.get('sell', 0) or 0
        net = buy - sell
        
        if date not in daily_data:
            daily_data[date] = {'foreign': 0, 'trust': 0, 'dealer': 0}
        
        if 'Foreign' in name or 'Dealer' in name:
            daily_data[date]['foreign'] += net
        elif 'Trust' in name or '投信' in name:
            daily_data[date]['trust'] += net
        elif 'Dealer' in name or '自營' in name:
            daily_data[date]['dealer'] += net
    
    for date, vals in daily_data.items():
        cur.execute('''
            INSERT OR REPLACE INTO MarketData (symbol, date, foreign_net, trust_net, dealer_net)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, date, vals['foreign'], vals['trust'], vals['dealer']))
    
    conn.commit()
    conn.close()
    return len(daily_data)

# Top 100 stocks to fetch
stocks = ['2330','2317','2303','2454','3034','3008','2002','1301','1326','1216',
    '2610','2615','2891','2881','5871','6505','3665','3017','2345','6230',
    '3583','2360','6139','3189','3443','1590','2308','2382','2408','2474',
    '3033','3231','3338','3702','4938','5880','6446','6669','6770',
    '8046','8454','8478','8499','3711','4961','2379','2451','2201','2207',
    '2231','2352','2353','2354','2356','2371','2373','2376','2383','2385',
    '2392','2393','2401','2402','2404','2412','2420','2423','2425','2426',
    '2427','2428','2429','2430','2431','2432','2433','2434','2436','2438',
    '2439','4952','6415','6183']

print('=' * 60)
print('Fetching Institutional Data for', len(stocks), 'stocks')
print('=' * 60)

total_saved = 0
for i, symbol in enumerate(stocks, 1):
    print(f'[{i}/{len(stocks)}] {symbol}...', end=' ', flush=True)
    data = fetch_inst_data(symbol)
    if data:
        count = save_inst_data(symbol, data)
        total_saved += count
        print(f'{count} days')
    else:
        print('No data')
    time.sleep(0.3)  # Rate limit

print()
print('=' * 60)
print(f'Done! Saved {total_saved} total days')
print('=' * 60)

# Verify
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('SELECT COUNT(DISTINCT symbol) FROM MarketData')
print('Total symbols now:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM MarketData')
print('Total rows:', cur.fetchone()[0])
conn.close()
