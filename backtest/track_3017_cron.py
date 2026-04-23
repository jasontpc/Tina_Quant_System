# -*- coding: utf-8 -*-
"""
3017 奇鋐 - 上漲追蹤 Cron Job
每 10 分鐘檢查一次，漲幅 >= 1% 時推播
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json
import os
from datetime import datetime

TRACK_FILE = 'Tina_Quant_System/data/3017_track.json'
ALERT_THRESHOLD = 1.0  # 1% 漲幅

def load_state():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'alerted': False, 'price': 0, 'change': 0}

def save_state(code, price, change, timestamp, alerted=False, alert_time=None):
    data = {
        'code': code,
        'price': price,
        'change': change,
        'timestamp': timestamp,
        'alerted': alerted
    }
    if alert_time:
        data['alert_time'] = alert_time
    with open(TRACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run():
    code = '3017'
    name = '奇鋐'
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    h = yf.Ticker(code + '.TW').history(period='5d')
    if len(h) < 2:
        print(f'[{now}] 3017 資料不足')
        return
    
    prices = list(h['Close'])
    current = float(prices[-1])
    prev = float(prices[-2])
    change = (current / prev - 1) * 100
    
    state = load_state()
    
    print(f'[{now}] 3017 奇鋐: {current:.2f} ({change:+.2f}%) | 已推播: {state.get("alerted", False)}')
    
    # 更新狀態
    save_state(code, current, change, now, state.get('alerted', False), state.get('alert_time'))
    
    # 漲幅觸發推播
    if change >= ALERT_THRESHOLD and not state.get('alerted', False):
        msg = f"""🔥 3017 奇鋐 上漲通知！

現價: {current:.2f}
漲幅: {change:+.2f}%
時間: {now}

突破 {ALERT_THRESHOLD}% 門檻！"""
        print(msg)
        save_state(code, current, change, now, True, now)
        print('\n[ALERT_TRIGGERED]')
        print(msg)

if __name__ == '__main__':
    run()