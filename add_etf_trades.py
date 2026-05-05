# -*- coding: utf-8 -*-
"""Sherry DCA 模擬交易 - 新增XLV/VHT/GLD進場"""
import sys, sqlite3, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = DATA + r'\sherry_sim_trades.db'

def main():
    print('=== Sherry DCA 模擬交易 - 新增進場 ===\n')
    
    if not os.path.exists(DB):
        print(f'找不到資料庫: {DB}')
        return
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 定義進場
    etfs = [
        ('XLV', 'Health Care Select Sector SPDR', 144.21, 33.2, 100),
        ('VHT', 'Vanguard Health Care ETF', 269.65, 37.8, 100),
        ('GLD', 'SPDR Gold Shares', 420.46, 39.6, 100),
    ]
    
    print(f'日期: {today}\n')
    
    for sym, name, price, rsi, shares in etfs:
        amount = price * shares
        try:
            cur.execute('''INSERT INTO open_positions 
                (symbol, entry_date, entry_price, shares, amount, entry_rsi, strategy, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'DCA_RSI', ?)''',
                (sym, today, price, shares, amount, rsi, today))
            conn.commit()
            print(f'+ {sym} ({name})')
            print(f'  進場價: ${price:.2f}')
            print(f'  數量: {shares}股')
            print(f'  金額: ${amount:.2f}')
            print(f'  RSI: {rsi}')
            print()
        except Exception as e:
            print(f'ERR {sym}: {e}')
    
    conn.close()
    
    # 顯示結果
    print('=== 當前持倉 ===\n')
    conn2 = sqlite3.connect(DB)
    cur2 = conn2.cursor()
    cur2.execute('SELECT symbol, entry_date, entry_price, shares, amount, entry_rsi FROM open_positions')
    for r in cur2.fetchall():
        sym, dt, px, sh, amt, rsi = r
        print(f'{sym}: {sh}股 @ ${px:.2f} = ${amt:.2f} (RSI={rsi})')
    conn2.close()

if __name__ == '__main__':
    main()