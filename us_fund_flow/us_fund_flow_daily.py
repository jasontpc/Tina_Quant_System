"""
美股資金流向每日報告腳本
US Fund Flow Daily Report Script
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fund_flow_database import fetch_fund_flow, save_db
import json
from datetime import datetime

def main():
    print("=" * 50)
    print("  US Fund Flow Database - Daily Update")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 抓取最新數據
    print("\n[1/3] Fetching fund flow data...")
    data = fetch_fund_flow(period='5d')
    
    # 儲存
    print("[2/3] Saving database...")
    path = save_db(data)
    print(f"      Saved to: {path}")
    
    # 顯示報告
    print("\n[3/3] Generating report...")
    print()
    print("=" * 50)
    print("[FUND FLOWS]")
    print("=" * 50)
    print(f"{'Symbol':<6} {'Name':<20} {'Close':>9} {'Change':>8} {'RSI':>6} {'Trend':<10}")
    print("-" * 50)
    
    # 分類顯示
    categories = ['equity', 'bond', 'commodity', 'currency', 'fear']
    category_names = {
        'equity': '[EQUITY] Stocks',
        'bond': '[BOND] Bonds',
        'commodity': '[COMMODITY] Commodities',
        'currency': '[CURRENCY] Currency',
        'fear': '[VIX] Volatility'
    }
    
    for cat in categories:
        first = True
        for sym, d in data['flows'].items():
            if d.get('type') == cat and 'error' not in d:
                if first:
                    print(f"\n  {category_names[cat]}")
                    first = False
                sign = '+' if d['change_pct'] > 0 else ''
                rsi_str = f"{d['rsi']:.0f}" if d['rsi'] else "N/A"
                print(f"    {sym:<5} {d['name']:<19} {d['close']:>9.2f} {sign}{d['change_pct']:>6.1f}% RSI={rsi_str:>4} {d['ma_trend']}")
    
    # 市場摘要
    print()
    print("=" * 50)
    print("[MARKET SUMMARY]")
    print("=" * 50)
    s = data['summary']
    
    print(f"\n  Risk On Score: {s['risk_on']:.1f}")
    print(f"  Risk Off Score: {s['risk_off']:.1f}")
    print(f"  Market Mode: ", end='')
    
    if s['market_mode'] == 'risk_on':
        print("[Risk On] - Risk Appetite")
    elif s['market_mode'] == 'risk_off':
        print("[Risk Off] - Risk Aversion")
    else:
        print("[Neutral] - Cautious")
    
    print("\n[Signals]")
    for sig in s['signals']:
        print(f"  - {sig}")
    
    # 警示
    alerts = []
    for sym, d in data['flows'].items():
        if 'error' not in d and d.get('rsi'):
            if d['type'] == 'fear' and d['rsi'] > 75:
                alerts.append(f"WARNING: {sym} RSI={d['rsi']:.0f} - Market Fear High")
            elif d['type'] == 'equity' and d['rsi'] > 85:
                alerts.append(f"WARNING: {sym} RSI={d['rsi']:.0f} - Stocks Overbought")
            elif d['type'] == 'bond' and d['rsi'] > 80:
                alerts.append(f"WARNING: {sym} RSI={d['rsi']:.0f} - Bonds Overbought")
    
    if alerts:
        print("\n[ALERTS]")
        for a in alerts:
            print(f"  ! {a}")
    
    print("\n" + "=" * 50)
    print("  Done!")
    print("=" * 50)

if __name__ == '__main__':
    main()
