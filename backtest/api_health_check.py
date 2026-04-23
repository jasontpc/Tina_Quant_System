# -*- coding: utf-8 -*-
"""
Tina API 健康檢查腳本 v2
1. 檢查所有 API 連線
2. 異常時推播 Telegram
3. 產出 JSON 報告
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import yfinance as yf
import sqlite3
from datetime import datetime
import json
import os

# 設定
DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'
REPORT_FILE = 'Tina_Quant_System/logs/api_health_check.json'
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1aNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
TELEGRAM_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
TELEGRAM_CHAT = '1616824689'

def send_telegram(msg):
    """發送 Telegram 通知"""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT, 'text': msg}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def check_twse():
    try:
        url = 'https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260423&stockNo=2330&response=json'
        r = requests.get(url, timeout=10)
        return (r.status_code == 200, 'OK' if r.status_code == 200 else f'HTTP {r.status_code}')
    except Exception as e:
        return False, str(e)

def check_yfinance():
    try:
        t = yf.Ticker('2330.TW')
        h = t.history(period='1d')
        if len(h) > 0:
            return True, f'2330={float(h["Close"].iloc[-1]):.0f}'
        return False, 'No data'
    except Exception as e:
        return False, str(e)

def check_sqlite():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM MarketData')
        count = cur.fetchone()[0]
        conn.close()
        return True, f'{count} records'
    except Exception as e:
        return False, str(e)

def check_fugle():
    try:
        from fugle_marketdata import RestClient
        api_key = 'NWNiNjgzMzAtZDM3Ni00MDg0LTk5OTQtYTI0MzlkMzdiOWFjIDczMThlOWJlLWNkY2UtNDhjNS1iNGEzLWRhYWUxYTJlNjZiZg=='
        client = RestClient(api_key=api_key)
        data = client.stock.technical.rsi(symbol='2330', period=14)
        return (data is not None, 'OK' if data else 'No data')
    except Exception as e:
        return False, str(e)

def check_finmind():
    try:
        url = 'https://api.finmindtrade.com/api/v4/data'
        headers = {'Authorization': 'Bearer ' + FINMIND_TOKEN}
        params = {'dataset': 'TaiwanStockInfo', 'data_id': '2330'}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        # 400 = 需要付費，不算錯誤
        if r.status_code == 200:
            return True, 'OK (Full)'
        elif r.status_code == 400:
            return True, 'OK (Basic only - paid feature)'
        else:
            return False, f'HTTP {r.status_code}'
    except Exception as e:
        return False, str(e)

def main():
    print('='*60)
    print(' Tina API 健康檢查 (v2)')
    print('='*60)
    print()
    
    apis = [
        ('TWSE', check_twse),
        ('yfinance', check_yfinance),
        ('SQLite', check_sqlite),
        ('Fugle', check_fugle),
        ('FinMind', check_finmind),
    ]
    
    results = []
    failed = []
    
    for name, func in apis:
        ok, detail = func()
        status = '[OK]' if ok else '[FAIL]'
        print(f' {name:12s} {status} {detail}')
        results.append({'name': name, 'ok': ok, 'detail': detail})
        if not ok:
            failed.append(name)
    
    print()
    print('='*60)
    
    all_ok = len(failed) == 0
    
    if all_ok:
        print(' 結論: 所有 API 正常運作')
    else:
        print(f' 結論: {len(failed)} 個 API 有問題: {", ".join(failed)}')
        # 發送 Telegram 通知
        msg = f"""[Tina API 警示] {datetime.now().strftime('%Y-%m-%d %H:%M')}

異常 API:
{chr(10).join(['- ' + f for f in failed])}

請檢查系統狀態！"""
        send_telegram(msg)
    
    print('='*60)
    
    # 儲存報告
    os.makedirs('Tina_Quant_System/logs', exist_ok=True)
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'all_ok': all_ok,
        'failed_count': len(failed),
        'failed_apis': failed,
        'results': results
    }
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f' 報告: {REPORT_FILE}')
    
    return all_ok, failed

if __name__ == '__main__':
    main()