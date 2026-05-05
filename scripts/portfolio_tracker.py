# -*- coding: utf-8 -*-
"""
Jo's Portfolio Database
本地持倉資料庫：歷史交易、年化報酬率、殖利率
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import time

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\portfolio.db'

# Jo's current holdings (from memory)
HOLDINGS = [
    {'symbol': '2382.TW', 'name': '2382 廣達', 'shares': 100, 'buy_price': 319.50, 'buy_date': '2026-04-30'},
    {'symbol': '00713.TW', 'name': '00713 高息低波', 'shares': 200, 'buy_price': 53.35, 'buy_date': '2026-04-30'},
]

# Historical trades
TRADES = [
    {'symbol': '00981A.TW', 'name': '00981A 國泰5G+', 'shares': 1000, 'buy_price': 26.95, 'buy_date': '2026-04-25', 'sell_price': 28.27, 'sell_date': '2026-04-30'},
]

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Holdings table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            shares REAL,
            buy_price REAL,
            buy_date TEXT,
            current_price REAL,
            market_value REAL,
            unrealized_pnl REAL,
            unrealized_pnl_pct REAL,
            updated_at TEXT,
            UNIQUE(symbol, buy_price, buy_date)
        )
    ''')
    
    # Trade history
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            shares REAL,
            buy_price REAL,
            buy_date TEXT,
            sell_price REAL,
            sell_date TEXT,
            realized_pnl REAL,
            realized_pnl_pct REAL,
            status TEXT DEFAULT 'closed',
            closed_at TEXT
        )
    ''')
    
    # Daily portfolio snapshots
    cur.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            total_value REAL,
            total_cost REAL,
            total_unrealized_pnl REAL,
            total_unrealized_pnl_pct REAL,
            cash REAL,
            updated_at TEXT
        )
    ''')
    
    conn.commit()
    return conn

def update_holdings(conn):
    """更新持倉現價"""
    cur = conn.cursor()
    total_value = 0
    total_cost = 0
    
    for h in HOLDINGS:
        sym = h['symbol']
        try:
            t = yf.Ticker(sym)
            h_data = t.history(period='1d')
            if h_data.empty:
                current_price = h['buy_price']  # fallback
            else:
                current_price = float(h_data['Close'].iloc[-1])
        except:
            current_price = h['buy_price']
        
        market_value = current_price * h['shares']
        cost = h['buy_price'] * h['shares']
        unrealized_pnl = market_value - cost
        unrealized_pnl_pct = (unrealized_pnl / cost * 100) if cost > 0 else 0
        
        total_value += market_value
        total_cost += cost
        
        # Upsert
        cur.execute('''
            INSERT OR REPLACE INTO holdings 
            (symbol, name, shares, buy_price, buy_date, current_price, market_value, unrealized_pnl, unrealized_pnl_pct, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (h['symbol'], h['name'], h['shares'], h['buy_price'], h['buy_date'],
              current_price, market_value, unrealized_pnl, unrealized_pnl_pct,
              datetime.now().strftime('%Y-%m-%d %H:%M')))
    
    conn.commit()
    return total_value, total_cost

def insert_trades(conn):
    """寫入歷史交易（預防重複）"""
    cur = conn.cursor()
    for t in TRADES:
        # Check if this trade already exists
        cur.execute('SELECT COUNT(*) FROM trades WHERE symbol=? AND buy_date=? AND sell_date=?',
                   (t['symbol'], t['buy_date'], t['sell_date']))
        exists = cur.fetchone()[0]
        if exists == 0:
            cur.execute('''
                INSERT INTO trades (symbol, name, shares, buy_price, buy_date, sell_price, sell_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'closed')
            ''', (t['symbol'], t['name'], t['shares'], t['buy_price'], t['buy_date'], t['sell_price'], t['sell_date']))
        
        # Recalculate PnL for closed trades
        cur.execute('''
            UPDATE trades SET realized_pnl=?, realized_pnl_pct=?, closed_at=?
            WHERE symbol=? AND buy_date=? AND sell_date=? AND (realized_pnl IS NULL OR realized_pnl = 0)
        ''', (
            (t['sell_price'] - t['buy_price']) * t['shares'],
            (t['sell_price'] / t['buy_price'] - 1) * 100,
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            t['symbol'], t['buy_date'], t['sell_date']
        ))
    
    conn.commit()

def calc_annualized_return(trade):
    """計算年化報酬率"""
    try:
        buy_date = datetime.strptime(trade['buy_date'], '%Y-%m-%d')
        sell_date_str = trade.get('sell_date')
        if sell_date_str:
            sell_date = datetime.strptime(sell_date_str, '%Y-%m-%d')
            end_price = trade['sell_price']
        else:
            sell_date = datetime.now()
            end_price = trade.get('current_price', trade['buy_price'])
        
        days = (sell_date - buy_date).days
        if days <= 0:
            days = 1
        
        years = days / 365.25
        total_return = (end_price / trade['buy_price'] - 1) * 100
        
        # Cap annualized return to reasonable bounds for display
        if years < 0.1:
            # For short holds, just show total return prorated
            annualized = total_return * (365.25 / days) if days > 0 else total_return
            if abs(annualized) > 500:
                annualized = total_return  # show total return instead of wild number
        else:
            annual_mult = (1 + total_return / 100) ** (1 / years)
            annualized = (annual_mult - 1) * 100
        
        return round(annualized, 1)
    except:
        return 0

def get_dividend_yield(symbol, current_price):
    """取得殖利率 (annualized TTM dividend / price)"""
    try:
        t = yf.Ticker(symbol)
        divs = t.dividends
        if len(divs) == 0:
            return 0
        
        # Use last 4 quarters of dividends (or all if < 4)
        last_4 = divs.tail(4)
        if len(last_4) == 0:
            return 0
        
        # Annualize: multiply by 4 if quarterly (4 entries), by 1 if only annual
        # But if we only have 1 entry, it's likely annual
        if len(divs) >= 4:
            ttm_div = last_4.sum()  # 4 quarters = 1 year
        elif len(divs) >= 2:
            # Interpolate: assume semi-annual if 2 entries
            ttm_div = last_4.sum() * 2
        else:
            ttm_div = last_4.sum()  # annual dividend
        
        yield_pct = (ttm_div / current_price * 100) if current_price > 0 else 0
        return round(yield_pct, 2)
    except:
        return 0

def main():
    conn = init_db()
    
    print()
    print('=' * 65)
    print('PORTFOLIO DATABASE UPDATE')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    print()
    
    # Update holdings
    print('[1] 持倉更新...')
    total_value, total_cost = update_holdings(conn)
    print(f'    總市值: ${total_value:,.2f} | 總成本: ${total_cost:,.2f}')
    
    # Insert trades
    print('[2] 歷史交易寫入...')
    insert_trades(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
    closed_trades = cur.fetchone()[0]
    print(f'    已記錄 {closed_trades} 筆歷史交易')
    
    # Portfolio snapshot
    today = datetime.now().strftime('%Y-%m-%d')
    unrealized_pnl = total_value - total_cost
    unrealized_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
    
    cur.execute('''
        INSERT OR REPLACE INTO portfolio_daily 
        (date, total_value, total_cost, total_unrealized_pnl, total_unrealized_pnl_pct, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (today, total_value, total_cost, unrealized_pnl, unrealized_pct,
          datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    
    # Display holdings
    print()
    print('[3] 持倉明細')
    print('-' * 65)
    print('股票          代號         股數    成本     現價      市值      帳面損益    報酬%')
    print('-' * 65)
    
    for h in HOLDINGS:
        sym = h['symbol']
        cur.execute('SELECT * FROM holdings WHERE symbol=?', (sym,))
        row = cur.fetchone()
        if row:
            name = row[2]
            shares = row[3]
            buy_p = row[4]
            current_p = row[6]
            market_v = row[7]
            pnl = row[8]
            pnl_pct = row[9]
            
            div_yield = get_dividend_yield(sym, current_p)
            annualized = calc_annualized_return({'buy_price': buy_p, 'buy_date': h['buy_date'], 'current_price': current_p})
            
            pnl_str = f'${pnl:>+8.0f}' if pnl else '$0'
            pnl_pct_str = f'{pnl_pct:>+6.1f}%' if pnl_pct else ' 0.0%'
            
            print(f'{name:<10} {sym:<10} {shares:>5}  ${buy_p:>7.2f}  ${current_p:>7.2f}  ${market_v:>8.0f}  {pnl_str:>10}  {pnl_pct_str:>7}')
            print(f'            殖利率: {div_yield:.2f}% | 年化報酬: {annualized:+.1f}%')
    
    # Closed trades
    print()
    print('[4] 歷史交易（含已實現損益）')
    print('-' * 65)
    cur.execute("SELECT * FROM trades WHERE status='closed' ORDER BY sell_date DESC")
    for row in cur.fetchall():
        sym, name, shares, buy_p, buy_d, sell_p, sell_d, pnl, pnl_pct = row[1:10]
        if sell_p and pnl:
            print(f'{name} | 買${buy_p} x {shares} | 賣${sell_p} | 獲利${pnl:,.0f} ({pnl_pct:+.1f}%)')
    
    # Summary
    print()
    print('=' * 65)
    print('SUMMARY')
    print('=' * 65)
    
    cur.execute('SELECT SUM(unrealized_pnl), SUM(unrealized_pnl_pct), SUM(market_value), SUM(buy_price * shares) FROM holdings')
    row = cur.fetchone()
    unrealized_total = row[0] or 0
    unrealized_pct_avg = row[1] or 0
    total_mv = row[2] or 0
    total_cost_calc = row[3] or 0
    
    print(f'總持倉價值: ${total_mv:,.2f}')
    print(f'總成本: ${total_cost_calc:,.2f}')
    print(f'帳面未實現損益: ${unrealized_total:,.2f} ({unrealized_pct_avg:+.1f}%)')
    
    # Realized from closed trades
    cur.execute('SELECT SUM(realized_pnl) FROM trades WHERE status="closed"')
    realized = cur.fetchone()[0] or 0
    print(f'已實現損益: ${realized:,.2f}')
    
    print()
    print(f'DB: {DB}')
    print('=' * 65)
    
    conn.close()
    return True

if __name__ == '__main__':
    main()