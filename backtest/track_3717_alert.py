# -*- coding: utf-8 -*-
"""
3717 晶澈 - 上漲即時推播
當漲幅 >= 3% 時推播通知
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json
import os
from datetime import datetime

TRACK_FILE = 'Tina_Quant_System/data/3717_track.json'
ALERT_THRESHOLD = 3.0  # 3% 漲幅

def load_last_price():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_last_price(code, price, change, timestamp):
    data = {
        'code': code,
        'price': price,
        'change': change,
        'timestamp': timestamp,
        'alerted': False
    }
    with open(TRACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_and_alert():
    code = '3717'
    name = '晶澈'
    
    h = yf.Ticker(code + '.TW').history(period='5d')
    if len(h) < 2:
        return None
    
    prices = list(h['Close'])
    current = float(prices[-1])
    prev = float(prices[-2])
    change = (current / prev - 1) * 100
    
    last = load_last_price()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    print(f"[{now}] 3717 晶澈: {current:.2f} ({change:+.2f}%)")
    
    # 首次記錄
    if last is None:
        save_last_price(code, current, change, now)
        print('  → 首次記錄價格')
        return None
    
    # 價格更新
    save_last_price(code, current, change, now)
    
    # 漲幅觸發
    if change >= ALERT_THRESHOLD and not last.get('alerted'):
        msg = f"""🔥 3717 晶澈 上漲通知！

現價: {current:.2f}
漲幅: {change:+.2f}%
時間: {now}

突破 {ALERT_THRESHOLD}% 門檻，已達通知標準！"""
        print(msg)
        # 標記已推播
        with open(TRACK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['alerted'] = True
        data['alert_time'] = now
        with open(TRACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return msg
    
    return None

if __name__ == '__main__':
    alert = check_and_alert()
    if alert:
        print('\n[ALERT_TRIGGERED]')