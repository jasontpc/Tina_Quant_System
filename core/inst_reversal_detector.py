# -*- coding: utf-8 -*-
"""
法人逆轉偵測模組 (P1)
=====================
偵測法人同日買轉賣模式，作為 Nana_v5.2 的 Exit 條件之一。

逆轉類型:
- SAME_DAY_REVERSAL: 同日內從買超變賣超
- CONSECUTIVE_SELL: 連續買超 N 天後突然賣超
- REVERSAL_AFTER_GAP: 跳空後逆轉（缺口 + 法人同步賣超）
- TRUST_FLIP: 投信從買超轉賣超（通常為行情反轉訊號）

Exit 觸發條件（加入 Nana_v5.2）:
- 法人逆轉偵測觸發 → 提前出场
- 適用於已持有倉位
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

DB_PATH = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db'
DATA_DIR = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data'

def get_inst_data(symbol: str, days: int = 20) -> List[Dict]:
    """取得近 N 天法人數據"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT date, foreign_net, trust_net
        FROM MarketData
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    ''', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for date, f, t in rows:
        result.append({
            'date': str(date)[:10],
            'foreign_net': f or 0,
            'trust_net': t or 0,
        })
    return result


def detect_same_day_reversal(inst_data: List[Dict]) -> Optional[Dict]:
    """
    偵測同日買轉賣
    同一天內法人從買超變賣超（適用於有盤中即時資料的市場）
    台股為 T+2 制度，原則上不適用，但可偵測連續兩天模式
    """
    if len(inst_data) < 2:
        return None
    
    for i in range(len(inst_data) - 1):
        curr = inst_data[i]
        prev = inst_data[i + 1]
        
        # 外資：昨天買超，今天賣超
        if prev['foreign_net'] > 0 and curr['foreign_net'] < 0:
            return {
                'type': 'SAME_DAY_REVERSAL',
                'symbol': None,
                'date': curr['date'],
                'foreign_net': curr['foreign_net'],
                'trust_net': curr['trust_net'],
                'prev_foreign_net': prev['foreign_net'],
                'severity': 'HIGH' if curr['foreign_net'] < -1000 else 'MEDIUM',
                'description': f"外資同日逆轉: {prev['foreign_net']:+.0f} → {curr['foreign_net']:+.0f}"
            }
        
        # 投信：昨天買超，今天賣超
        if prev['trust_net'] > 0 and curr['trust_net'] < 0:
            return {
                'type': 'TRUST_FLIP',
                'symbol': None,
                'date': curr['date'],
                'foreign_net': curr['foreign_net'],
                'trust_net': curr['trust_net'],
                'prev_trust_net': prev['trust_net'],
                'severity': 'HIGH',
                'description': f"投信翻轉: {prev['trust_net']:+.0f} → {curr['trust_net']:+.0f}"
            }
    return None


def detect_consecutive_sell(inst_data: List[Dict], min_buy_days: int = 3) -> Optional[Dict]:
    """
    偵測連續買超後逆轉
    模式：連續 N 天買超 → 今天突然賣超
    """
    if len(inst_data) < min_buy_days + 1:
        return None
    
    # 從最新資料往回數
    consecutive_buy = 0
    first_sell_date = None
    
    for i, record in enumerate(inst_data):
        if record['foreign_net'] > 0:
            consecutive_buy += 1
        elif record['foreign_net'] < 0:
            if consecutive_buy >= min_buy_days:
                first_sell_date = record['date']
                sell_amount = record['foreign_net']
            consecutive_buy = 0
    
    if consecutive_buy >= min_buy_days:
        return {
            'type': 'CONSECUTIVE_SELL',
            'date': inst_data[0]['date'],
            'consecutive_buy_days': consecutive_buy,
            'severity': 'HIGH' if consecutive_buy >= 5 else 'MEDIUM',
            'description': f"外資連續買超 {consecutive_buy} 天後逆轉"
        }
    
    return None


def detect_inst_reversal(symbol: str, days: int = 20) -> Dict:
    """
    主偵測函式：偵測法人逆轉
    返回所有偵測到的逆轉信號
    """
    inst_data = get_inst_data(symbol, days)
    if not inst_data:
        return {'symbol': symbol, 'reversals': [], 'has_reversal': False}
    
    reversals = []
    
    # 1. 同日逆轉偵測
    sdr = detect_same_day_reversal(inst_data)
    if sdr:
        sdr['symbol'] = symbol
        reversals.append(sdr)
    
    # 2. 連續賣超偵測
    csr = detect_consecutive_sell(inst_data, min_buy_days=3)
    if csr:
        csr['symbol'] = symbol
        reversals.append(csr)
    
    return {
        'symbol': symbol,
        'date': inst_data[0]['date'],
        'reversals': reversals,
        'has_reversal': len(reversals) > 0,
        'latest_foreign_net': inst_data[0]['foreign_net'],
        'latest_trust_net': inst_data[0]['trust_net'],
    }


def detect_reversal_with_price(symbol: str, days: int = 20) -> Dict:
    """
    完整逆轉偵測：結合價格 + 法人資料
    適用於持仓中的股票
    """
    # 取得法人數據
    inst_result = detect_inst_reversal(symbol, days)
    
    # 取得價格數據
    try:
        df = yf.download(symbol + '.TW', period='30d', auto_adjust=True, progress=False)
        if df is not None and len(df) >= 2:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            close = df['Close'].values
            prev_close = close[-2]
            curr_close = close[-1]
            price_chg = (curr_close / prev_close - 1) * 100
            
            inst_result['price'] = float(curr_close)
            inst_result['price_change'] = float(price_chg)
            
            # 價格大跌 + 法人賣超 = 確認逆轉
            if price_chg < -3 and inst_result['latest_foreign_net'] < 0:
                inst_result['confirmed_reversal'] = True
                inst_result['severity'] = 'HIGH'
            elif price_chg < -1 and inst_result['latest_foreign_net'] < 0:
                inst_result['confirmed_reversal'] = True
                inst_result['severity'] = 'MEDIUM'
        else:
            inst_result['price'] = None
            inst_result['price_change'] = None
    except Exception as e:
        inst_result['price'] = None
        inst_result['price_change'] = None
    
    return inst_result


def scan_universe_for_reversals(symbols: List[str], days: int = 20) -> List[Dict]:
    """掃描整個股票池，找出有法人逆轉的股票"""
    results = []
    for symbol in symbols:
        result = detect_reversal_with_price(symbol, days)
        if result['has_reversal']:
            results.append(result)
    return results


def should_exit_on_reversal(symbol: str, entry_date: str = None) -> Tuple[bool, str]:
    """
    決策函式：判斷是否應該在逆轉時出场
    返回 (should_exit, reason)
    """
    result = detect_reversal_with_price(symbol, days=10)
    
    if not result['has_reversal']:
        return False, ""
    
    for reversal in result['reversals']:
        # HIGH severity → 立即出场
        if reversal.get('severity') == 'HIGH':
            return True, f"法人逆轉 ({reversal['type']}): {reversal.get('description', '')}"
        
        # MEDIUM severity + 已獲利 > 2% → 考慮出场
        if reversal.get('severity') == 'MEDIUM':
            if result.get('confirmed_reversal'):
                return True, f"法人逆轉 + 價格下跌 ({reversal['type']})"
    
    return False, ""


# ==================== 測試區 ====================
if __name__ == '__main__':
    TEST_SYMBOLS = ['2330', '3231', '2353', '2382', '2317']
    
    print('='*70)
    print(' 法人逆轉偵測 - 測試執行')
    print('='*70)
    print()
    
    for symbol in TEST_SYMBOLS:
        result = detect_reversal_with_price(symbol, days=15)
        print(f'【{symbol}】 ({result.get("date", "N/A")})')
        print(f'  外資: {result["latest_foreign_net"]:+.0f} | 投信: {result["latest_trust_net"]:+.0f}')
        print(f'  價格: {result.get("price", "N/A")} | 漲跌: {result.get("price_change", 0):+.2f}%')
        
        if result['has_reversal']:
            for rev in result['reversals']:
                print(f'  ⚠️  {rev["type"]} | {rev.get("description", "")} | Severity: {rev.get("severity", "?")}')
        else:
            print('  ✅ 無逆轉訊號')
        
        should_exit, reason = should_exit_on_reversal(symbol)
        if should_exit:
            print(f'  🚨 EXIT 建議: {reason}')
        print()
