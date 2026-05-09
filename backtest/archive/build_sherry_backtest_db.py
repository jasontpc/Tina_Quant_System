# -*- coding: utf-8 -*-
"""Sherry ETF DCA Historical Backtest Database"""
import sys, sqlite3, json, yfinance
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_backtest.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def build_backtest_db():
    """Build historical backtest database for DCA strategy"""
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Sherry ETF DCA 回測資料庫建置                ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # DCA simulation results table
    cur.execute('''CREATE TABLE IF NOT EXISTS dca_sim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        monthly_amount REAL NOT NULL,
        total_invested REAL DEFAULT 0,
        total_shares REAL DEFAULT 0,
        avg_cost REAL DEFAULT 0,
        final_value REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        return_pct REAL DEFAULT 0,
        annualized REAL DEFAULT 0,
        years INTEGER DEFAULT 0,
        trades INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, start_date, monthly_amount)
    )''')
    
    # Monthly investment records
    cur.execute('''CREATE TABLE IF NOT EXISTS dca_monthly (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        invest_date TEXT NOT NULL,
        price REAL NOT NULL,
        shares REAL NOT NULL,
        amount REAL NOT NULL,
        cumulative_shares REAL DEFAULT 0,
        cumulative_invested REAL DEFAULT 0,
        current_value REAL DEFAULT 0,
        return_pct REAL DEFAULT 0,
        rsi_14 REAL DEFAULT 50,
        zone TEXT DEFAULT 'NEUTRAL',
        UNIQUE(symbol, invest_date)
    )''')
    
    # Strategy comparison table
    cur.execute('''CREATE TABLE IF NOT EXISTS strategy_compare (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        strategy TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        return_pct REAL DEFAULT 0,
        annualized REAL DEFAULT 0,
        max_drawdown REAL DEFAULT 0,
        sharpe_ratio REAL DEFAULT 0,
        trades INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, strategy, start_date)
    )''')
    
    conn.commit()
    
    # ETF list
    etfs = ['SPY', 'QQQ', 'VTI', 'IVV', 'IWM', 'XLK', 'XLF', 'XLV', 'XLE', 'XLY',
             'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'VGT', 'VHT', 'VYM', 'VNQ', 'SCHD',
             'BND', 'AGG', 'TLT', 'HYG', 'LQD', 'VEU', 'VXUS', 'EFA', 'EEM',
             'SSO', 'QLD', 'TQQQ', 'SPXL', 'GLD', 'SLV', 'USO']
    
    # Parameters
    MONTHLY_AMOUNTS = [1000, 2000, 5000]
    START_DATES = ['2021-01-01', '2022-01-01', '2023-01-01', '2024-01-01']
    
    print(f'ETF數量: {len(etfs)}')
    print(f'每月金額: {MONTHLY_AMOUNTS}')
    print(f'起始日期: {START_DATES}')
    print()
    
    total_sims = 0
    
    for sym in etfs:
        print(f'處理 {sym}...', end=' ', flush=True)
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='10y')
            
            if len(hist) < 500:
                print(f'不足 {len(hist)}筆')
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            # Run simulations for each start date
            for start_dt in START_DATES:
                if start_dt > dates[-1]:
                    continue
                    
                # Find start index
                start_idx = next((i for i, d in enumerate(dates) if d >= start_dt), 0)
                
                # Get data from start date
                sim_dates = dates[start_idx:]
                sim_closes = closes[start_idx:]
                
                if len(sim_dates) < 100:
                    continue
                
                for monthly in MONTHLY_AMOUNTS:
                    # DCA simulation
                    total_invested = 0
                    total_shares = 0
                    current_month = ''
                    monthly_records = []
                    
                    for i in range(len(sim_dates)):
                        date = sim_dates[i]
                        price = sim_closes[i]
                        month = date[:7]
                        
                        # Buy at start of month
                        if month != current_month:
                            shares = monthly / price
                            total_shares += shares
                            total_invested += monthly
                            current_month = month
                            
                            # Get RSI at this point
                            rsi = calc_rsi(sim_closes[:i+1])
                            
                            zone = 'OVERSOLD' if rsi < 30 else ('OVERBOUGHT' if rsi > 70 else 'NEUTRAL')
                            
                            # Current value
                            curr_value = total_shares * price
                            ret_pct = (curr_value - total_invested) / total_invested * 100 if total_invested > 0 else 0
                            
                            monthly_records.append({
                                'date': date,
                                'price': price,
                                'shares': shares,
                                'amount': monthly,
                                'cumulative_shares': total_shares,
                                'cumulative_invested': total_invested,
                                'current_value': curr_value,
                                'return_pct': ret_pct,
                                'rsi': rsi,
                                'zone': zone
                            })
                    
                    # Calculate final stats
                    final_price = sim_closes[-1]
                    final_value = total_shares * final_price
                    total_return = final_value - total_invested
                    return_pct = (total_return / total_invested) * 100 if total_invested > 0 else 0
                    years = len(monthly_records) / 12
                    annualized = ((final_value / total_invested) ** (1/years) - 1) * 100 if years > 0 and total_invested > 0 else 0
                    avg_cost = total_invested / total_shares if total_shares > 0 else 0
                    
                    # Save simulation
                    cur.execute('''INSERT OR REPLACE INTO dca_sim 
                        (symbol, start_date, end_date, monthly_amount, total_invested, total_shares,
                         avg_cost, final_value, total_return, return_pct, annualized, years, trades)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (sym, start_dt, sim_dates[-1], monthly, total_invested, total_shares,
                         avg_cost, final_value, total_return, return_pct, annualized, int(years), len(monthly_records)))
                    
                    # Save monthly records
                    for rec in monthly_records:
                        cur.execute('''INSERT OR REPLACE INTO dca_monthly 
                            (symbol, invest_date, price, shares, amount, cumulative_shares,
                             cumulative_invested, current_value, return_pct, rsi_14, zone)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (sym, rec['date'], rec['price'], rec['shares'], rec['amount'],
                             rec['cumulative_shares'], rec['cumulative_invested'],
                             rec['current_value'], rec['return_pct'], rec['rsi'], rec['zone']))
                    
                    total_sims += 1
            
            conn.commit()
            print(f'OK')
        
        except Exception as e:
            print(f'ERROR: {e}')
    
    # Final stats
    print(f'\n\n{"="*50}')
    print(f'=== Sherry 回測資料庫建置完成 ===')
    print(f'{"="*50}')
    
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM dca_sim')
    syms = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM dca_sim')
    sims = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM dca_monthly')
    records = cur.fetchone()[0]
    
    print(f'DCA模擬: {sims}筆')
    print(f'每月記錄: {records:,}筆')
    print(f'ETF數量: {syms}')
    
    # Best simulations
    print(f'\n=== 最佳DCA模擬（總報酬 > 50%）===')
    cur.execute('''SELECT symbol, start_date, monthly_amount, return_pct, annualized, years
        FROM dca_sim WHERE return_pct > 50 ORDER BY return_pct DESC LIMIT 15''')
    print(f'{"ETF":<8} {"起始":<12} {"月額":>8} {"總報酬":>10} {"年化":>8} {"年份":>6}')
    print('-' * 55)
    for r in cur.fetchall():
        print(f'{r[0]:<8} {r[1]:<12} ${r[2]:>7,} {r[3]:>+9.1f}% {r[4]:>7.1f}% {r[5]:>5}年')
    
    # Category averages
    print(f'\n=== ETF類別平均表現 ===')
    cur.execute('''SELECT 
        CASE 
            WHEN symbol IN ('SSO','QLD','TQQQ','SPXL') THEN '槓桿型'
            WHEN symbol IN ('GLD','SLV','USO') THEN '商品型'
            WHEN symbol IN ('BND','AGG','TLT','HYG','LQD') THEN '債券型'
            WHEN symbol IN ('VYM','SCHD') THEN '收益型'
            WHEN symbol IN ('VEU','VXUS','EFA','EEM') THEN '國際型'
            ELSE '指數/產業型'
        END as category,
        AVG(return_pct) as avg_return,
        AVG(annualized) as avg_annual,
        COUNT(*) as count
        FROM dca_sim WHERE years >= 2
        GROUP BY category ORDER BY avg_return DESC''')
    print(f'{"類別":<12} {"平均報酬":>10} {"平均年化":>10} {"數量":>6}')
    print('-' * 40)
    for r in cur.fetchall():
        print(f'{r[0]:<12} {r[1]:>+9.1f}% {r[2]:>9.1f}% {r[3]:>6}')
    
    import os
    db_size = os.path.getsize(DB) / (1024 * 1024)
    print(f'\nDB Size: {db_size:.1f} MB')
    
    conn.close()

if __name__ == '__main__':
    build_backtest_db()