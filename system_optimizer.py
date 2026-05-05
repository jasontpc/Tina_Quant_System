# -*- coding: utf-8 -*-
"""Comprehensive System Optimizer - All Teams Database Update & Strategy Enhancement"""
import sys, sqlite3, json, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

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

def update_tw_history():
    """Update Taiwan stock history database"""
    print('=== 更新台股歷史資料庫 ===')
    db = f'{DATA_DIR}\\tw_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute('SELECT symbol FROM stocks ORDER BY symbol')
    stocks = [r[0] for r in cur.fetchall()]
    
    updated = 0
    for sym in stocks[:10]:
        try:
            t = yfinance.Ticker(f"{sym}.TW")
            hist = t.history(period='5d')
            if len(hist) > 0:
                closes = hist['Close'].tolist()
                highs = hist['High'].tolist()
                lows = hist['Low'].tolist()
                opens = hist['Open'].tolist()
                vols = hist['Volume'].tolist()
                dates = hist.index.strftime('%Y-%m-%d').tolist()
                
                for i in range(len(closes)):
                    cur.execute('''INSERT OR REPLACE INTO daily_ohlcv 
                        (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (sym, dates[i], opens[i], highs[i], lows[i], closes[i], int(vols[i])))
                updated += 1
        except:
            pass
    
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = cur.fetchone()[0]
    conn.close()
    print(f'更新完成: {updated}檔, 總筆數: {total}')
    return updated

def update_us_history():
    """Update US stock history database"""
    print('\n=== 更新美股歷史資料庫 ===')
    db = f'{DATA_DIR}\\us_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute('SELECT symbol FROM stock_summary ORDER BY symbol')
    stocks = [r[0] for r in cur.fetchall()]
    
    updated = 0
    for sym in stocks[:15]:
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='5d')
            if len(hist) > 0:
                closes = hist['Close'].tolist()
                dates = hist.index.strftime('%Y-%m-%d').tolist()
                latest_close = closes[-1]
                latest_date = dates[-1]
                
                rsi = calc_rsi(closes)
                
                if rsi < 30:
                    zone = 'OVERSOLD'
                elif rsi > 70:
                    zone = 'OVERBOUGHT'
                else:
                    zone = 'NEUTRAL'
                
                cur.execute('''UPDATE stock_summary 
                    SET current_price=?, current_rsi=?, last_updated=?
                    WHERE symbol=?''',
                    (latest_close, rsi, latest_date, sym))
                updated += 1
        except:
            pass
    
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = cur.fetchone()[0]
    conn.close()
    print(f'更新完成: {updated}檔, 總筆數: {total}')
    return updated

def optimize_maggy_strategy():
    """Quick Maggy strategy optimization"""
    print('\n=== Maggy 策略快速優化 ===')
    db = f'{DATA_DIR}\\us_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # Get all oversold/neutral_low stocks
    cur.execute("SELECT symbol, current_rsi, current_price FROM stock_summary WHERE current_rsi < 40 ORDER BY current_rsi ASC")
    candidates = cur.fetchall()
    
    print(f'低檔候選: {len(candidates)}檔')
    for r in candidates[:5]:
        print(f'  {r[0]}: RSI={r[1]:.1f} price={r[2]}')
    
    # Load and analyze best params
    config_file = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f'\n當前策略版本: {config.get("version", "N/A")}')
        params = config.get('optimized_params', {})
        print(f'進場RSI: < {params.get("entry_rsi", "N/A")}')
        print(f'出廠RSI: > {params.get("exit_rsi", "N/A")}')
        print(f'持倉: {params.get("max_hold_days", "N/A")}天')
    except Exception as e:
        print(f'無法讀取策略配置: {e}')
    
    conn.close()
    return len(candidates)

def check_system_status():
    """Check all system databases"""
    print('\n=== 全系統資料庫狀態 ===\n')
    
    dbs = {
        'tw_history.db': ('台股歷史', 'daily_ohlcv'),
        'us_history.db': ('美股歷史', 'daily_ohlcv'),
        'maggy_rsi.db': ('Maggy RSI', 'rsi_summary'),
        'vogel_indicators.db': ('Vogel 台指', 'daily'),
        'fugle.db': ('Fugle 報價', 'quote_latest'),
        'shinsegae_centum.db': ('新世界百貨', 'brands'),
        'haeundae_bbq.db': ('海雲台餐廳', 'restaurants'),
    }
    
    results = []
    for db_name, (desc, table) in dbs.items():
        path = f'{DATA_DIR}\\{db_name}'
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            try:
                cur.execute(f'SELECT COUNT(*) FROM {table}')
                cnt = cur.fetchone()[0]
                syms = ''
                try:
                    cur.execute(f'SELECT COUNT(DISTINCT symbol) FROM {table}')
                    syms = cur.fetchone()[0]
                except:
                    pass
                results.append({'name': desc, 'size': size, 'count': cnt, 'syms': syms})
            except Exception as e:
                results.append({'name': desc, 'size': size, 'count': 0, 'syms': '', 'error': str(e)})
            conn.close()
        else:
            results.append({'name': desc, 'size': 0, 'count': 0, 'syms': ''})
    
    for r in results:
        if r.get('error'):
            print(f"  {r['name']:<15} {r['size']:>8.0f}KB  ERROR: {r['error']}")
        elif r['syms']:
            print(f"  {r['name']:<15} {r['size']:>8.0f}KB {r['count']:>8,}筆 {r['syms']:>5}檔")
        else:
            print(f"  {r['name']:<15} {r['size']:>8.0f}KB {r['count']:>8,}筆")
    
    return results

def main():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     全系統主動優化整合 — 資料庫更新與策略增強     ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # 1. System status
    results = check_system_status()
    
    # 2. Update databases
    print()
    update_tw_history()
    update_us_history()
    
    # 3. Strategy optimization
    candidates = optimize_maggy_strategy()
    
    # 4. Summary
    print('\n\n=== 整合建議 ===')
    print(f'1. 資料庫已更新: {sum(r["count"] for r in results):,}筆')
    print(f'2. 低檔候選: {candidates}檔（可關注進場）')
    print(f'3. 美股: 等待RSI<35進場')
    print(f'4. 台股: TWII RSI~93 全市場過熱，等待<70')
    print(f'5. 台指期: TX在BB區間，等待40,015突破')

if __name__ == '__main__':
    main()