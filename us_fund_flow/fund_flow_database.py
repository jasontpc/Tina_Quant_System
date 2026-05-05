"""
美股資金流向資料庫
US Market Fund Flow Database
"""

import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_DIR = Path(__file__).parent / "data"

# 資金流向 ETF 清單
FLOW_ETFS = {
    # 股票型
    'SPY': {'name': 'S&P 500', 'type': 'equity', 'category': 'US_large'},
    'QQQ': {'name': 'Nasdaq 100', 'type': 'equity', 'category': 'US_tech'},
    'IWM': {'name': 'Russell 2000', 'type': 'equity', 'category': 'US_small'},
    'VEA': {'name': 'Developed ex-US', 'type': 'equity', 'category': 'intl'},
    'EEM': {'name': 'Emerging Markets', 'type': 'equity', 'category': 'em'},
    
    # 債券型
    'TLT': {'name': '20+ Year Treasury', 'type': 'bond', 'category': 'long_bond'},
    'IEF': {'name': '7-10 Year Treasury', 'type': 'bond', 'category': 'mid_bond'},
    'SHV': {'name': 'Short Treasury', 'type': 'bond', 'category': 'short_bond'},
    'BND': {'name': 'Total Bond', 'type': 'bond', 'category': 'total_bond'},
    
    # 另類資產
    'GLD': {'name': 'Gold', 'type': 'commodity', 'category': 'gold'},
    'IAU': {'name': 'Gold (iShares)', 'type': 'commodity', 'category': 'gold'},
    'SLV': {'name': 'Silver', 'type': 'commodity', 'category': 'silver'},
    
    # 貨幣/大宗
    'UUP': {'name': 'US Dollar', 'type': 'currency', 'category': 'usd'},
    'VIXY': {'name': 'VIX Short-Term', 'type': 'fear', 'category': 'vix'},
}

def get_db_path(date_str=None):
    """取得資料庫檔案路徑"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    return DB_DIR / f"fund_flow_{date_str}.json"

def load_latest_db():
    """載入最新資料庫"""
    files = sorted(DB_DIR.glob("fund_flow_*.json"), reverse=True)
    if files:
        with open(files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def fetch_fund_flow(date=None, period='5d', rsi_period='3mo'):
    """
    抓取資金流向數據
    date: 指定日期 (YYYY-MM-DD)
    period: 歷史區間 (5d, 1mo, 3mo, 6mo, 1y)
    rsi_period: RSI 計算用的歷史區間
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    results = {
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'flows': {},
        'summary': {}
    }
    
    for sym, info in FLOW_ETFS.items():
        try:
            t = yf.Ticker(sym)
            hist_short = t.history(period=period)
            hist_long = t.history(period=rsi_period)
            
            if len(hist_short) >= 2:
                close_prices = hist_short['Close']
                volumes = hist_short['Volume']
                
                # 計算資金流向指標
                latest_close = float(close_prices.iloc[-1])
                prev_close = float(close_prices.iloc[-2])
                price_change = latest_close - prev_close
                price_pct = (price_change / prev_close) * 100
                
                # 使用成交量變化作為流向參考
                if len(volumes) >= 5:
                    avg_volume = volumes.iloc[-5:].mean()
                    latest_volume = volumes.iloc[-1]
                    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
                else:
                    volume_ratio = 1
                
                # 5日/20日均線判斷趨勢
                if len(close_prices) >= 20:
                    ma5 = close_prices.iloc[-5:].mean()
                    ma20 = close_prices.iloc[-20:].mean()
                    ma_trend = 'bullish' if latest_close > ma20 else 'bearish'
                elif len(close_prices) >= 5:
                    ma5 = close_prices.iloc[-5:].mean()
                    ma_trend = 'bullish' if latest_close > ma5 else 'bearish'
                else:
                    ma_trend = 'neutral'
                
                # RSI 使用更長期的數據計算
                close_long = hist_long['Close']
                deltas = close_long.diff()
                gains = deltas.clip(lower=0).rolling(14).mean()
                losses = (-deltas.clip(upper=0)).rolling(14).mean()
                rs = gains / losses
                rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if len(rs) >= 14 else None
                
                results['flows'][sym] = {
                    'name': info['name'],
                    'type': info['type'],
                    'category': info['category'],
                    'close': round(latest_close, 2),
                    'change_pct': round(price_pct, 2),
                    'volume_ratio': round(volume_ratio, 2),
                    'ma_trend': ma_trend,
                    'rsi': round(rsi, 1) if rsi else None
                }
        except Exception as e:
            results['flows'][sym] = {'error': str(e)}
    
    # 資金流向摘要
    results['summary'] = analyze_flows(results['flows'])
    
    return results

def analyze_flows(flows):
    """分析資金流向"""
    summary = {
        'risk_on': 0,
        'risk_off': 0,
        'signals': []
    }
    
    # 計算各類型資金流向分數
    for sym, data in flows.items():
        if 'error' in data or 'rsi' not in data:
            continue
        
        rsi = data.get('rsi', 50)
        change_pct = data.get('change_pct', 0)
        
        if data['type'] == 'equity':
            if change_pct > 0 and rsi < 70:
                summary['risk_on'] += change_pct
            elif change_pct < 0:
                summary['risk_off'] += abs(change_pct)
        
        elif data['type'] == 'bond':
            if change_pct > 0:
                summary['risk_off'] += change_pct
            else:
                summary['risk_on'] += abs(change_pct)
        
        elif data['type'] == 'commodity':
            if sym in ['GLD', 'IAU'] and change_pct > 0:
                summary['risk_off'] += change_pct * 0.5  # 黃金避險
            elif sym == 'SLV' and change_pct > 0:
                summary['risk_on'] += change_pct * 0.5  # 白銀動能
        
        elif data['type'] == 'fear':
            if rsi is not None:
                if rsi > 70:
                    summary['signals'].append(f'{sym} RSI={rsi} 市場恐慌')
                elif rsi < 30:
                    summary['signals'].append(f'{sym} RSI={rsi} 市場貪婪')
    
    # 總結信號
    if summary['risk_on'] > summary['risk_off'] * 1.5:
        summary['market_mode'] = 'risk_on'
        summary['signals'].append('資金流向: 風險偏好主導')
    elif summary['risk_off'] > summary['risk_on'] * 1.5:
        summary['market_mode'] = 'risk_off'
        summary['signals'].append('資金流向: 避險情緒主導')
    else:
        summary['market_mode'] = 'neutral'
        summary['signals'].append('資金流向: 中性觀望')
    
    return summary

def save_db(data, date=None):
    """儲存資料庫"""
    if date is None:
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    path = get_db_path(date)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return path

def get_historical_report(days=30):
    """取得歷史資金流向報告"""
    files = sorted(DB_DIR.glob("fund_flow_*.json"), reverse=True)[:days]
    reports = []
    
    for f in files:
        with open(f, 'r', encoding='utf-8') as fp:
            reports.append(json.load(fp))
    
    return reports

if __name__ == '__main__':
    print("=== 美股資金流向資料庫 ===")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    data = fetch_fund_flow(period='5d')
    save_db(data)
    
    print("【資金流向】")
    for sym, d in data['flows'].items():
        if 'error' not in d:
            sign = '+' if d['change_pct'] > 0 else ''
            rsi_str = str(d['rsi']) if d['rsi'] else 'N/A'
            print(f"  {sym:5} {d['name']:20} {d['close']:8} {sign}{d['change_pct']}% RSI={rsi_str}")
    
    print()
    print("【市場摘要】")
    s = data['summary']
    print(f"  風險偏好分: {s['risk_on']:.1f}")
    print(f"  避險分數: {s['risk_off']:.1f}")
    print(f"  市場模式: {s['market_mode']}")
    for sig in s['signals']:
        print(f"  -> {sig}")
