# -*- coding: utf-8 -*-
"""Maggy Advanced Strategies - 進階獲利策略"""
import sys, yfinance, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
OUTPUT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\advanced_strategies.json'

def get_earnings_dates():
    """Get upcoming earnings dates for watchlist stocks"""
    # Known earnings dates (approximate - verify before use)
    earnings = {
        'AAPL': '2026-05-01',  # end of April
        'MSFT': '2026-04-28',  # late April
        'GOOGL': '2026-04-29',  # late April
        'AMZN': '2026-05-01',
        'META': '2026-05-01',
        'NVDA': '2026-05-15',
        'TSLA': '2026-04-23',  # past
        'AMD': '2026-05-05',
    }
    return earnings

def calc_iv_rank(symbol):
    """Calculate implied volatility rank (simplified)"""
    try:
        t = yfinance.Ticker(symbol)
        # Get options expiration dates (simplified - no IV calc)
        opt = t.option_chain('2026-05-15')
        if len(opt.calls) > 0:
            call_iv = opt.calls['impliedVolatility'].iloc[0] if 'impliedVolatility' in opt.calls.columns else 0.3
            return call_iv * 100
    except:
        pass
    return 50  # default moderate IV

def earnings_play_strategy(symbol, days_before=7, days_after=14):
    """
    Earnings Play Strategy:
    - Before earnings: Buy calls if stock in uptrend (RSI 40-60)
    - After earnings: Sell covered calls on big moves
    
    Note: Simplified version - real trading requires options data
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Check recent RSI trend
    cur.execute('SELECT date, close, rsi_14 FROM daily WHERE symbol=? ORDER BY date DESC LIMIT 20', (symbol,))
    rows = cur.fetchall()
    conn.close()
    
    if len(rows) < 20:
        return None
    
    recent_rsi = [r[2] for r in reversed(rows)]
    current_rsi = recent_rsi[-1]
    avg_rsi = sum(recent_rsi) / len(recent_rsi)
    
    # Signal
    if 40 <= current_rsi <= 60 and avg_rsi > 45:
        return {
            'type': 'EARNINGS_SETUP',
            'direction': 'BULLISH',
            'reason': f'RSI {current_rsi:.1f} in sweet spot before earnings',
            'iv_rank': calc_iv_rank(symbol),
        }
    elif current_rsi > 75:
        return {
            'type': 'EARNINGS_SETUP',
            'direction': 'OVERBOUGHT',
            'reason': f'RSI {current_rsi:.1f} too high, premium selling only',
            'iv_rank': calc_iv_rank(symbol),
        }
    
    return None

def sector_rotation_strategy():
    """
    Sector Rotation Strategy:
    - Identify strongest sector
    - Buy leaders in that sector
    
    Based on: Relative strength vs SPY
    """
    sectors = {
        'XLK': 'Technology',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'VGT': 'Info Tech',
    }
    
    results = []
    for sym, name in sectors.items():
        try:
            t = yfinance.Ticker(sym)
            spy = yfinance.Ticker('SPY')
            
            hist = t.history(period='60d')
            spy_hist = spy.history(period='60d')
            
            if len(hist) < 50:
                continue
            
            t_return = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
            spy_return = (spy_hist['Close'].iloc[-1] - spy_hist['Close'].iloc[0]) / spy_hist['Close'].iloc[0] * 100
            
            rel_strength = t_return - spy_return
            
            results.append({
                'sector_etf': sym,
                'sector_name': name,
                '60d_return': t_return,
                'spy_return': spy_return,
                'relative_strength': rel_strength,
                'signal': 'STRONG' if rel_strength > 5 else ('WEAK' if rel_strength < -5 else 'NEUTRAL'),
            })
        except:
            pass
    
    return sorted(results, key=lambda x: x['relative_strength'], reverse=True)

def options_income_strategy(symbol, days_to_expiry=30, strike_pct=5):
    """
    Covered Call Income Strategy:
    - Own 100 shares
    - Sell OTM call at strike = price * (1 + strike_pct/100)
    - Collect premium
    
    This is a simplified simulation
    """
    try:
        t = yfinance.Ticker(symbol)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        
        # Estimate premium (simplified - real IV needed)
        estimated_premium = price * 0.03  # ~3% of price
        
        return {
            'strategy': 'COVERED_CALL',
            'symbol': symbol,
            'stock_price': price,
            'estimated_strike': price * (1 + strike_pct / 100),
            'estimated_premium': estimated_premium,
            'income_pct': estimated_premium / price * 100,
            'days_to_expiry': days_to_expiry,
            'note': 'Use real options data for accurate premium calculation'
        }
    except:
        return None

def momentum_breakout_strategy(symbol, lookback=20, atr_mult=2):
    """
    Momentum Breakout Strategy:
    - Price breaks above 20-day high
    - RSI < 70 (not overheated)
    - ATR-based stop loss
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT date, close, high, low, rsi_14, atr_14 FROM daily WHERE symbol=? ORDER BY date DESC LIMIT ?', (symbol, lookback + 10))
    rows = cur.fetchall()
    conn.close()
    
    if len(rows) < lookback + 5:
        return None
    
    data = [{'date': r[0], 'close': r[1], 'high': r[2], 'low': r[3], 'rsi': r[4], 'atr': r[5]} for r in reversed(rows)]
    
    # Recent highs
    recent_closes = [d['close'] for d in data[-lookback:]]
    recent_highs = [d['high'] for d in data[-lookback:]]
    high_20 = max(recent_highs)
    
    current_close = data[-1]['close']
    current_rsi = data[-1]['rsi']
    atr = data[-1]['atr'] or current_close * 0.02
    
    # Signal
    if current_close > high_20 and current_rsi < 70:
        return {
            'strategy': 'MOMENTUM_BREAKOUT',
            'direction': 'LONG',
            'entry': current_close,
            'stop_loss': current_close - atr_mult * atr,
            'target': current_close + atr_mult * 3 * atr,
            'rsi': current_rsi,
            'reason': f'Breakout above {lookback}d high, RSI={current_rsi:.1f}'
        }
    elif current_close < recent_closes[0] * 0.9:
        return {
            'strategy': 'MOMENTUM_BREAKOUT',
            'direction': 'SHORT',
            'entry': current_close,
            'stop_loss': current_close + atr_mult * atr,
            'target': current_close - atr_mult * 2 * atr,
            'rsi': current_rsi,
            'reason': 'Below 20d low, momentum bearish'
        }
    
    return None

def main():
    print('=== Maggy 進階獲利策略系統 ===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # 1. Sector Rotation
    print('📊 產業輪動分析（60日相對強度）')
    sectors = sector_rotation_strategy()
    if sectors:
        for s in sectors:
            sig = '🟢' if s['signal'] == 'STRONG' else ('🔴' if s['signal'] == 'WEAK' else '⚪')
            print(f'{sig} {s["sector_etf"]} ({s["sector_name"]}): ret={s["60d_return"]:+.1f}% vs SPY={s["spy_return"]:+.1f}% rel={s["relative_strength"]:+.1f}')
    
    print()
    
    # 2. Earnings Setups
    print('📋 財報前的股票篩選')
    earnings_dates = get_earnings_dates()
    for sym, date in list(earnings_dates.items())[:5]:
        setup = earnings_play_strategy(sym)
        if setup:
            print(f'  {sym} ({date}): {setup["direction"]} - {setup["reason"]}')
    
    print()
    
    # 3. Momentum Breakouts (watchlist)
    print('📈 動量突破信號（等待進場）')
    watchlist = ['COIN', 'AMD', 'INTC', 'NFLX', 'TSLA']
    breakout_candidates = []
    for sym in watchlist:
        signal = momentum_breakout_strategy(sym)
        if signal:
            breakout_candidates.append({**signal, 'symbol': sym})
            print(f'  {sym}: {signal["direction"]} @ {signal["entry"]:.0f} stop={signal["stop_loss"]:.0f}')
    
    print()
    
    # 4. Options Income
    print('💰 選擇權收入策略（備用）')
    income_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    for sym in income_stocks:
        inc = options_income_strategy(sym)
        if inc:
            print(f'  {sym}: strike={inc["estimated_strike"]:.0f} premium={inc["estimated_premium"]:.0f} ({inc["income_pct"]:.1f}%)')
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'sector_rotation': sectors,
        'earnings_setups': [({'symbol': sym, 'date': date} | (earnings_play_strategy(sym) or {})) for sym, date in earnings_dates.items()],
        'momentum_breakouts': breakout_candidates,
    }
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 進階策略分析完成')

if __name__ == '__main__':
    main()