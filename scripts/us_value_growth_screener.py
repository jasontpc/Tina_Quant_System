# -*- coding: utf-8 -*-
"""
US Value Growth Screener - FIXED
三層過濾網：基礎濾網 → 基本面健康 → 技術面與動能
價格 < $100 USD
"""

import sqlite3
import yfinance as yf
import pandas as pd
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = f'{DATA_DIR}\\us_value_growth.db'

BASE_PRICE_MAX = 100
BASE_VOL_MIN = 1_000_000
BASE_MCAP_MIN = 500_000_000
FUND_PE_MAX = 30
FUND_PE_MIN = 0
FUND_ROE_MIN = 5
FUND_REV_GROWTH_MIN = 0
FUND_OP_MARGIN_MIN = 0
FUND_DEBT_RATIO_MAX = 80
FUND_DIV_YIELD_MIN = 0
TECH_RSI_MIN = 30
TECH_RSI_MAX = 70
TECH_BIAS20_MAX = 15
TECH_VOL_SURGE = 0.5

CANDIDATE_STOCKS = [
    'AMD', 'INTC', 'NVDA', 'AVGO', 'QCOM', 'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC',
    'NXPI', 'MCHP', 'ADI', 'XLNX', 'SWKS', 'QRVO', 'MPWR', 'ON', 'FSLR',
    'NET', 'MU', 'AKAM', 'FFIV', 'CARG', 'CVLT', 'BAND', 'NSRGY',
    'ISRG', 'DXCM', 'ALGN', 'HOLX', 'STE', 'TMO', 'DHR', 'ABT',
    'BMY', 'MRK', 'PFE', 'JNJ', 'UNH', 'CVS', 'AMGN', 'GILD',
    'AXP', 'C', 'COF', 'SCHW', 'SPGI', 'ICE', 'FITB', 'HBAN',
    'AMZN', 'HD', 'LOW', 'TGT', 'COST', 'WMT', 'DG', 'DLTR',
    'CAT', 'DE', 'BA', 'LMT', 'RTX', 'NOC', 'GD',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
    'NEE', 'DUK', 'SO', 'D', 'EMATERIALS',
    'AAPL', 'MSFT', 'GOOGL', 'META', 'NFLX',
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS fundamentals (symbol TEXT PRIMARY KEY, name_en TEXT, price REAL, market_cap REAL, shares_outstanding REAL, pe_ratio REAL, forward_pe REAL, eps REAL, revenue REAL, rev_growth REAL, op_margin REAL, roe REAL, debt_ratio REAL, div_yield REAL, beta REAL, updated_at TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS technicals (symbol TEXT PRIMARY KEY, price REAL, volume REAL, vol_avg_20 REAL, rsi_14 REAL, rsi_30 REAL, ma5 REAL, ma20 REAL, ma60 REAL, bias5 REAL, bias20 REAL, bias60 REAL, bb_upper REAL, bb_lower REAL, bb_position REAL, mom_5d REAL, mom_20d REAL, mom_1m REAL, mom_3m REAL, high_52w REAL, low_52w REAL, pos_52w REAL, ma_align_text TEXT, updated_at TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS scores (symbol TEXT PRIMARY KEY, base_pass INTEGER, fund_pass INTEGER, tech_pass INTEGER, fund_score REAL, tech_score REAL, mom_score REAL, total_score REAL, signal TEXT, updated_at TEXT)')
    cur.execute('DELETE FROM scores')
    conn.commit()
    return conn

def calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])

def analyze_stock(symbol):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='6mo')
        
        if h is None:
            return None
        if h.empty:
            return None
        if len(h) < 30:
            return None
        
        price = float(h['Close'].iloc[-1])
        vol_today = int(h['Volume'].iloc[-1])
        vol_avg20 = int(h['Volume'].rolling(20).mean().iloc[-1])
        
        if price >= BASE_PRICE_MAX:
            return None
        
        c = h['Close'].reset_index(drop=True)
        
        info = {}
        try:
            info = t.info or {}
        except:
            pass
        
        market_cap = info.get('marketCap', 0)
        shares = info.get('sharesOutstanding', 0)
        pe = info.get('trailingPE', None)
        fwd_pe = info.get('forwardPE', None)
        eps = info.get('trailingEps', None)
        rev = info.get('totalRevenue', 0)
        rev_growth = info.get('revenueGrowth', 0) or 0
        op_margin = info.get('operatingMargins', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        debt_ratio = (info.get('totalDebt', 0) / info.get('totalAssets', 1) * 100) if info.get('totalAssets', 0) else 50
        div_yield = info.get('dividendYield', 0) or 0
        beta = info.get('beta', 1) or 1
        name_en = info.get('longName', '') or info.get('quoteTypeName', '')
        
        rsi14 = calc_rsi(c.values, 14)
        rsi30 = calc_rsi(c.values, 30)
        
        ma5 = float(c.rolling(5).mean().iloc[-1])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        ma60 = float(c.rolling(60).mean().iloc[-1]) if len(c) >= 60 else ma20
        
        bias5 = (price / ma5 - 1) * 100
        bias20 = (price / ma20 - 1) * 100
        bias60 = (price / ma60 - 1) * 100 if ma60 > 0 else 0
        
        bb_std = float(c.rolling(20).std().iloc[-1])
        bb_upper = ma20 + 2 * bb_std
        bb_lower = ma20 - 2 * bb_std
        bb_position = (price - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper > bb_lower else 50
        
        mom5d = float((c.iloc[-1] / c.iloc[-6] - 1) * 100) if len(c) >= 6 else 0
        mom20d = float((c.iloc[-1] / c.iloc[-21] - 1) * 100) if len(c) >= 21 else 0
        mom1m = float((c.iloc[-1] / c.iloc[-22] - 1) * 100) if len(c) >= 22 else 0
        mom3m = float((c.iloc[-1] / c.iloc[-63] - 1) * 100) if len(c) >= 63 else 0
        
        high52 = float(c.iloc[-252:].max()) if len(c) >= 252 else float(c.max())
        low52 = float(c.iloc[-252:].min()) if len(c) >= 252 else float(c.min())
        pos52 = (price - low52) / (high52 - low52) * 100 if high52 > low52 else 50
        
        ma_align = price > ma5 > ma20 > ma60
        ma_align_text = 'P>MA5>MA20>MA60' if ma_align else (
            'P>MA5>MA20' if price > ma5 > ma20 else (
            'P>MA5' if price > ma5 else 'BELOW_MA5'))
        
        base_pass = (
            price < BASE_PRICE_MAX and
            vol_today >= BASE_VOL_MIN and
            market_cap >= BASE_MCAP_MIN
        )
        
        fund_pass = (
            pe and FUND_PE_MIN < pe <= FUND_PE_MAX and
            roe >= FUND_ROE_MIN / 100 and
            rev_growth >= FUND_REV_GROWTH_MIN and
            op_margin >= FUND_OP_MARGIN_MIN and
            debt_ratio <= FUND_DEBT_RATIO_MAX and
            div_yield >= FUND_DIV_YIELD_MIN
        )
        
        vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
        
        tech_pass = (
            rsi14 and TECH_RSI_MIN <= rsi14 <= TECH_RSI_MAX and
            bias20 < TECH_BIAS20_MAX and
            vol_ratio >= TECH_VOL_SURGE
        )
        
        fund_score = 0
        if pe and 5 <= pe <= 20: fund_score += 20
        elif pe and 20 < pe <= 30: fund_score += 10
        if fwd_pe and fwd_pe < pe: fund_score += 10
        if rev_growth > 0.2: fund_score += 20
        elif rev_growth > 0.1: fund_score += 10
        elif rev_growth > 0: fund_score += 5
        if op_margin > 0.2: fund_score += 15
        elif op_margin > 0.1: fund_score += 10
        elif op_margin > 0: fund_score += 5
        if roe > 0.2: fund_score += 15
        elif roe > 0.1: fund_score += 10
        elif roe > 0.05: fund_score += 5
        if div_yield > 0.03: fund_score += 10
        elif div_yield > 0.01: fund_score += 5
        
        tech_score = 0
        if rsi14 and 35 <= rsi14 <= 60: tech_score += 20
        elif rsi14 and 30 <= rsi14 < 35: tech_score += 10
        if bias20 < 5 and bias20 > -5: tech_score += 15
        elif bias20 < 10 and bias20 > -10: tech_score += 10
        if ma_align: tech_score += 20
        elif price > ma5 > ma20: tech_score += 10
        if bb_position > 80: tech_score += 5
        if price > bb_upper: tech_score += 10
        
        mom_score = 0
        if mom5d > 2: mom_score += 10
        elif mom5d > 0: mom_score += 5
        if mom20d > 10: mom_score += 15
        elif mom20d > 5: mom_score += 10
        elif mom20d > 0: mom_score += 5
        if mom1m > 15: mom_score += 15
        elif mom1m > 10: mom_score += 10
        elif mom1m > 5: mom_score += 5
        if mom3m > 20: mom_score += 10
        
        total_score = fund_score + tech_score + mom_score
        
        if total_score >= 80 and base_pass and fund_pass and tech_pass:
            signal = 'STRONG_BUY'
        elif total_score >= 60 and base_pass and fund_pass:
            signal = 'BUY'
        elif total_score >= 40 and base_pass:
            signal = 'HOLD'
        elif total_score >= 25:
            signal = 'CAUTION'
        else:
            signal = 'WAIT'
        
        return {
            'symbol': symbol,
            'name_en': name_en,
            'base_pass': int(base_pass),
            'fund_pass': int(fund_pass),
            'tech_pass': int(tech_pass),
            'fund': {
                'price': price, 'market_cap': market_cap, 'shares': shares,
                'pe': pe, 'forward_pe': fwd_pe, 'eps': eps, 'rev': rev,
                'rev_growth': rev_growth, 'op_margin': op_margin,
                'roe': roe, 'debt_ratio': debt_ratio, 'div_yield': div_yield, 'beta': beta
            },
            'tech': {
                'price': price, 'volume': vol_today, 'vol_avg20': vol_avg20,
                'rsi14': rsi14, 'rsi30': rsi30,
                'ma5': ma5, 'ma20': ma20, 'ma60': ma60,
                'bias5': bias5, 'bias20': bias20, 'bias60': bias60,
                'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_position': bb_position,
                'mom5d': mom5d, 'mom20d': mom20d, 'mom1m': mom1m, 'mom3m': mom3m,
                'high52': high52, 'low52': low52, 'pos52': pos52,
                'ma_align': ma_align_text
            },
            'score': {
                'fund': fund_score, 'tech': tech_score, 'mom': mom_score,
                'total': total_score, 'signal': signal
            }
        }
    except Exception as e:
        return None

def save_results(conn, results):
    cur = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for r in results:
        if not r:
            continue
        sym = r['symbol']
        f = r['fund']
        t = r['tech']
        s = r['score']
        cur.execute('INSERT OR REPLACE INTO fundamentals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sym, r['name_en'], t['price'], f['market_cap'], f['shares'],
             f['pe'], f['forward_pe'], f['eps'], f['rev'], f['rev_growth'], f['op_margin'],
             f['roe'], f['debt_ratio'], f['div_yield'], f['beta'], now))
        cur.execute('INSERT OR REPLACE INTO technicals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (sym, t['price'], t['volume'], t['vol_avg20'],
             t['rsi14'], t['rsi30'],
             t['ma5'], t['ma20'], t['ma60'], t['bias5'], t['bias20'], t['bias60'],
             t['bb_upper'], t['bb_lower'], t['bb_position'],
             t['mom5d'], t['mom20d'], t['mom1m'], t['mom3m'],
             t['high52'], t['low52'], t['pos52'], t['ma_align'], now))
        cur.execute('INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?,?,?,?,?,?)',
            (sym, r['base_pass'], r['fund_pass'], r['tech_pass'],
             s['fund'], s['tech'], s['mom'], s['total'], s['signal'], now))
    conn.commit()
    return len(results)

def main():
    print('=' * 70)
    print('US VALUE GROWTH SCREENER — 三層過濾網（股價 < $100 USD）')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 70)
    print()
    
    conn = init_db()
    print(f'Database: {DB_PATH}')
    print(f'Stocks: {len(CANDIDATE_STOCKS)} candidates')
    print()
    
    print('【三層過濾網條件】')
    print(f'  第一層-基礎：股價 < ${BASE_PRICE_MAX} | 成交量 > {BASE_VOL_MIN:,} | 市值 > ${BASE_MCAP_MIN/1e6:.0f}M')
    print(f'  第二層-基本面：PE 0-{FUND_PE_MAX} | ROE > {FUND_ROE_MIN}% | 營收成長 > 0%')
    print(f'            營益率 > 0 | 負債比 < {FUND_DEBT_RATIO_MAX}% | 股息率 > 0')
    print(f'  第三層-技術面：RSI {TECH_RSI_MIN}-{TECH_RSI_MAX} | BIAS20 < {TECH_BIAS20_MAX}%')
    print(f'            成交量突破{TECH_VOL_SURGE}倍 | 均線多頭排列')
    print()
    
    print('[1] Analyzing...')
    results = []
    layer1_pass = layer2_pass = layer3_pass = 0
    
    for sym in CANDIDATE_STOCKS:
        r = analyze_stock(sym)
        if r:
            results.append(r)
            if r['base_pass']:
                layer1_pass += 1
            if r['fund_pass']:
                layer2_pass += 1
            if r['tech_pass']:
                layer3_pass += 1
            s = r['score']
            if s['total'] >= 60 and r['base_pass'] and r['fund_pass']:
                t = r['tech']
                print(f'  {r["symbol"]}: ${t["price"]:.2f} | Score={s["total"]} | {s["signal"]}')
    
    analyzed = len(results)
    print(f'  Analyzed: {analyzed}/{len(CANDIDATE_STOCKS)} stocks')
    
    print()
    print('[2] Filter Pass Rates...')
    if analyzed > 0:
        print(f'  Layer 1 (Base) Pass: {layer1_pass}/{analyzed} ({layer1_pass*100/analyzed:.0f}%)')
        print(f'  Layer 2 (Fund) Pass: {layer2_pass}/{analyzed} ({layer2_pass*100/analyzed:.0f}%)')
        print(f'  Layer 3 (Tech) Pass: {layer3_pass}/{analyzed} ({layer3_pass*100/analyzed:.0f}%)')
    
    print()
    print('[3] Saving to database...')
    n = save_results(conn, results)
    print(f'  Saved: {n} records')
    
    sorted_r = sorted(results, key=lambda x: x['score']['total'], reverse=True)
    
    print()
    print('[4] Top 15 Candidates...')
    print()
    print(f'{"Rank":<5} {"Symbol":<8} {"Price":>8} {"RSI":>5} {"BIAS20":>7} {"MA排列":<18} {"Score":>6} {"Signal"}')
    print('-' * 80)
    for i, r in enumerate(sorted_r[:15], 1):
        sym = r['symbol']
        t = r['tech']
        s = r['score']
        rsi_str = f'{t["rsi14"]:.1f}' if t['rsi14'] else 'N/A'
        ma_text = t['ma_align'][:16]
        print(f'{i:<5} {sym:<8} {t["price"]:>8.2f} {rsi_str:>5} {t["bias20"]:>+7.1f}% {ma_text:<18} {s["total"]:>6.0f} {s["signal"]}')
    
    print()
    print('[5] Filter Pass Details...')
    print(f'{"Symbol":<8} {"Base":<5} {"Fund":<5} {"Tech":<5} {"PE":>6} {"ROE":>6} {"RSI":>5} {"MA排列"}')
    print('-' * 65)
    for r in sorted_r[:15]:
        f = r['fund']
        t = r['tech']
        pe_str = f'{f["pe"]:.1f}' if f['pe'] else 'N/A'
        roe_str = f'{f["roe"]*100:.1f}%' if f['roe'] else 'N/A'
        rsi_str = f'{t["rsi14"]:.1f}' if t['rsi14'] else 'N/A'
        print(f'{r["symbol"]:<8} {"Y" if r["base_pass"] else "N":<5} {"Y" if r["fund_pass"] else "N":<5} {"Y" if r["tech_pass"] else "N":<5} {pe_str:>6} {roe_str:>6} {rsi_str:>5} {t["ma_align"]}')
    
    print()
    print('[6] Summary')
    cur = conn.cursor()
    cur.execute('SELECT signal, COUNT(*) FROM scores GROUP BY signal ORDER BY MAX(total_score) DESC')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]} stocks')
    
    conn.close()
    print()
    print('=' * 70)
    print('DONE')

if __name__ == '__main__':
    main()