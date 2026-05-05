# -*- coding: utf-8 -*-
"""Sherry ETF DCA Backtester - Test DCA Strategy Performance"""
import sys, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_etf.db'
OUTPUT = f'{DATA_DIR}\\sherry_dca_results.json'

def dca_backtest():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Sherry ETF DCA 回測系統                      ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get ETFs
    cur.execute("SELECT symbol, name, category FROM etf_summary ORDER BY symbol")
    etfs = cur.fetchall()
    
    results = []
    
    print('=== DCA 回測（每月$1000，持续5年）===\n')
    
    for sym, name, cat in etfs[:20]:  # Test top 20
        # Get 5 years of data
        cur.execute('''SELECT date, close FROM etf_daily 
            WHERE symbol=? ORDER BY date LIMIT 1260''',
            (sym,))
        rows = cur.fetchall()
        
        if len(rows) < 500:
            continue
        
        dates = [r[0] for r in rows]
        closes = [r[1] for r in rows]
        
        # Simulate DCA: invest $1000/month for 5 years
        monthly_amount = 1000
        total_invested = 0
        total_shares = 0
        monthly_investments = []
        
        # Monthly DCA
        current_month = ''
        for i in range(0, len(dates), 1):
            date = dates[i]
            month = date[:7]
            price = closes[i]
            
            if month != current_month:
                # Buy for this month
                shares = monthly_amount / price
                total_shares += shares
                total_invested += monthly_amount
                current_month = month
                monthly_investments.append({
                    'date': date,
                    'price': price,
                    'shares': shares,
                    'invested': monthly_amount,
                    'total_shares': total_shares,
                    'total_invested': total_invested
                })
        
        # Calculate current value
        current_price = closes[-1]
        current_value = total_shares * current_price
        total_return = current_value - total_invested
        return_pct = (total_return / total_invested) * 100
        avg_cost = total_invested / total_shares if total_shares > 0 else 0
        
        # Annualized return (assuming 5 years)
        years = len(monthly_investments) / 12
        annualized = ((current_value / total_invested) ** (1/years) - 1) * 100 if years > 0 else 0
        
        results.append({
            'symbol': sym,
            'name': name,
            'category': cat,
            'total_invested': total_invested,
            'current_value': current_value,
            'total_return': total_return,
            'return_pct': return_pct,
            'annualized': annualized,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'months': len(monthly_investments)
        })
    
    # Sort by return
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    
    print(f'{"代號":<8} {"名稱":<16} {"投入":>10} {"市值":>10} {"報酬":>10} {"年化":>8}')
    print('-' * 70)
    for r in results[:15]:
        print(f'{r["symbol"]:<8} {r["name"][:16]:<16} ${r["total_invested"]:>9,.0f} ${r["current_value"]:>9,.0f} {r["return_pct"]:>+9.1f}% {r["annualized"]:>7.1f}%')
    
    # Category performance
    print('\n\n=== 類別平均表現 ===')
    cat_perf = {}
    for r in results:
        cat = r['category']
        if cat not in cat_perf:
            cat_perf[cat] = []
        cat_perf[cat].append(r['return_pct'])
    
    print(f'{"類別":<15} {"ETF數":>6} {"平均報酬":>10} {"年化報酬":>10}')
    print('-' * 45)
    for cat, rets in sorted(cat_perf.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
        avg = sum(rets) / len(rets)
        print(f'{cat:<15} {len(rets):>6} {avg:>+10.1f}%')
    
    # Best DCA ETFs
    print('\n\n=== 🏆 最佳DCA標的 TOP 10 ===')
    for i, r in enumerate(results[:10], 1):
        icon = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else '  '))
        print(f'{icon} {i:>2}. {r["symbol"]:<8} {r["return_pct"]:>+7.1f}% ({r["annualized"]:>.1f}%/年) {r["name"]}')
    
    # Save results
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 回測結果已儲存: {OUTPUT}')
    
    conn.close()
    return results

if __name__ == '__main__':
    dca_backtest()