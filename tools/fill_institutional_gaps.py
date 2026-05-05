#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動填補法人資料缺口
功能：
1. 檢查 MarketData 中各股票的缺口
2. 自動從 FinMind API 抓取資料
3. 更新 MarketData 表
"""

import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import json

DB_PATH = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db'

def get_missing_dates(symbol, days=10):
    """檢查股票近N日是否有缺口"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT date FROM MarketData 
        WHERE symbol=? AND date >= date('now', '-7 days')
        ORDER BY date
    ''', (symbol,))
    
    existing = set(row[0] for row in cur.fetchall())
    conn.close()
    
    # 生成近7個交易日
    today = datetime.now().strftime('%Y-%m-%d')
    dates = []
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        if d not in existing and d <= today:
            dates.append(d)
    
    return dates

def fill_gap(symbol, date):
    """填補特定股票某日的資料缺口"""
    print(f'  填補 {symbol} {date}...')
    # TODO: 實作 FinMind API 抓取邏輯
    # 目前先用 yfinance 估算法人資料
    return False

def check_and_fill_all():
    """檢查並填補所有股票的缺口"""
    print('=== 法人資料缺口檢查 ===')
    print()
    
    # 主要關注股票清單
    stocks = ['2379', '3231', '2353', '2385', '2454', '2330']
    
    gaps = {}
    for symbol in stocks:
        missing = get_missing_dates(symbol)
        if missing:
            gaps[symbol] = missing
            print(f'{symbol}: 缺少 {len(missing)} 筆資料 - {missing}')
        else:
            print(f'{symbol}: 無缺口')
    
    print()
    if not gaps:
        print('✓ 所有股票資料完整')
        return
    
    print(f'共 {len(gaps)} 檔股票有缺口需要填補')
    print('請安裝 finmind-api 並執行 fill_institutional_gaps.py --fill')
    
    # 嘗試使用 yfinance 取得價格資料作為參考
    for symbol, dates in gaps.items():
        for date in dates:
            fill_gap(symbol, date)

if __name__ == '__main__':
    import sys
    check_and_fill_all()
    
    if '--fill' in sys.argv:
        print('執行填補模式...')
        # TODO: 實作 FinMind 填補邏輯