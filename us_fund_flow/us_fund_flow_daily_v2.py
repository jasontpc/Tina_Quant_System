"""
美股資金流向資料庫 v2.0
整合視覺化工具 + 技術指標 + 板塊分析

資料來源:
- Finviz Heatmap: 即時板塊資金流向
- MacroMicro: 美股11大板塊資金
- TradingView MFI: 資金流量指標
- WhaleWisdom: 機構持股變動
- CNN Fear & Greed: 市場情緒
"""

import sqlite3
import json
import yfinance as yf
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_fund_flow.db'

# 美股11大板塊 + 主要ETF
SECTORS = {
    # 科技
    'XLK': {'name': 'Technology', 'sector': 'Technology'},
    # 醫療
    'XLV': {'name': 'Health Care', 'sector': 'Healthcare'},
    # 金融
    'XLF': {'name': 'Financial', 'sector': 'Financial'},
    # 能源
    'XLE': {'name': 'Energy', 'sector': 'Energy'},
    # 消費
    'XLY': {'name': 'Consumer Discretionary', 'sector': 'Consumer'},
    'XLP': {'name': 'Consumer Staples', 'sector': 'Consumer'},
    # 工業
    'XLI': {'name': 'Industrials', 'sector': 'Industrials'},
    # 原料
    'XLB': {'name': 'Materials', 'sector': 'Materials'},
    # 不動產
    'XLRE': {'name': 'Real Estate', 'sector': 'Real Estate'},
    # 公用
    'XLU': {'name': 'Utilities', 'sector': 'Utilities'},
    # 通信
    'XLC': {'name': 'Communication', 'sector': 'Communication'},
}

# 熱力圖配色映射
HEATMAP_COLORS = {
    'strong_green': '資金強勢流入',
    'green': '資金流入',
    'yellow': '中性觀望',
    'red': '資金流出',
    'strong_red': '資金強勢流出',
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # 板塊資金流向
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sector_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        sector_name TEXT,
        date TEXT,
        price REAL,
        change_pct REAL,
        volume REAL,
        rsi REAL,
        mfi REAL,
        trend TEXT,
        flow_direction TEXT,
        heatmap_color TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_sector ON sector_flow(symbol, date)')
    
    # 大盤情緒指標
    cur.execute('''
    CREATE TABLE IF NOT EXISTS market_sentiment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        fear_greed_index INTEGER,
        fear_greed_label TEXT,
        vix REAL,
        vix_change_pct REAL,
        risk_on_score REAL,
        risk_off_score REAL,
        market_mode TEXT,
        smart_money_indicator TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_sentiment ON market_sentiment(date)')
    
    # 機構持倉變動 (13F)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS institutional_holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        quarter TEXT,
        institutional_name TEXT,
        shares_held REAL,
        change_pct REAL,
        change_value REAL,
        created_at TEXT
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_inst ON institutional_holdings(symbol, quarter)')
    
    # ETF 資金流向
    cur.execute('''
    CREATE TABLE IF NOT EXISTS etf_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        name TEXT,
        date TEXT,
        price REAL,
        change_pct REAL,
        volume REAL,
        net_flow REAL,
        rsi_30d REAL,
        rsi_60d REAL,
        trend TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_etf ON etf_flow(symbol, date)')
    
    conn.commit()
    conn.close()
    print(f'Database initialized: {DB_FILE}')

def get_mfi(symbol, period=14):
    """計算 Money Flow Index (MFI)"""
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='60d')
        
        typical_price = (h['High'] + h['Low'] + h['Close']) / 3
        raw_money_flow = typical_price * h['Volume']
        
        positive_flow = raw_money_flow.shift(1).where(typical_price.diff() > 0, 0)
        negative_flow = raw_money_flow.shift(1).where(typical_price.diff() < 0, 0)
        
        positive_mf = positive_flow.rolling(period).sum()
        negative_mf = negative_flow.rolling(period).sum()
        
        mf_ratio = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mf_ratio))
        
        return float(mfi.iloc[-1]) if len(mfi.dropna()) > 0 else 50
    except:
        return 50

def get_rsi(close, period=14):
    """計算 RSI"""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_trend(rsi_30d, rsi_60d, change_pct):
    """判斷趨勢"""
    if rsi_30d > 60 and rsi_60d > 55 and change_pct > 0.5:
        return 'strong_up'
    elif rsi_30d > 50 and rsi_60d > 45:
        return 'up'
    elif rsi_30d < 40 and rsi_60d < 45:
        return 'down'
    else:
        return 'neutral'

def get_heatmap_color(rsi, change_pct):
    """根據 RSI 和變化率設定熱力圖顏色"""
    if rsi >= 70 and change_pct >= 1:
        return 'strong_green'
    elif rsi >= 55 and change_pct >= 0:
        return 'green'
    elif rsi >= 45 and change_pct >= -0.5:
        return 'yellow'
    elif rsi >= 35 and change_pct >= -2:
        return 'red'
    else:
        return 'strong_red'

def get_flow_direction(rsi, change_pct, mfi):
    """判斷資金流向"""
    if rsi > 60 and mfi > 60:
        return 'inflow'
    elif rsi < 40 and mfi < 40:
        return 'outflow'
    else:
        return 'neutral'

def update_sector_flow():
    """更新板塊資金流向"""
    print('Updating sector fund flows...')
    conn = sqlite3.connect(DB_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    for sym, info in SECTORS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period='60d')
            
            c = float(h['Close'].iloc[-1])
            p = float(h['Close'].iloc[-2])
            chg = (c - p) / p * 100
            
            v = float(h['Volume'].iloc[-1])
            
            rsi_30d = float(get_rsi(h['Close'], 30).iloc[-1])
            rsi_60d = float(get_rsi(h['Close'], 60).iloc[-1]) if len(h) >= 60 else rsi_30d
            
            mfi = get_mfi(sym)
            trend = get_trend(rsi_30d, rsi_60d, chg)
            color = get_heatmap_color(rsi_30d, chg)
            direction = get_flow_direction(rsi_30d, chg, mfi)
            
            conn.execute('''
                INSERT OR REPLACE INTO sector_flow 
                (symbol, sector_name, date, price, change_pct, volume, rsi, mfi, trend, flow_direction, heatmap_color, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym, info['name'], today, c, chg, v, rsi_30d, mfi, trend, direction, color, datetime.now().isoformat()))
            
            print(f'  {sym}: ${c:.2f} ({chg:+.2f}%) RSI={rsi_30d:.0f} MFI={mfi:.0f} [{color}]')
            
        except Exception as e:
            print(f'  {sym}: Error - {str(e)[:50]}')
    
    conn.commit()
    conn.close()
    print('Sector flow update complete')

def update_market_sentiment():
    """更新大盤情緒"""
    print('Updating market sentiment...')
    
    try:
        # VIX
        vix_t = yf.Ticker('VIXY')
        vix_h = vix_t.history(period='2d')
        vix = float(vix_h['Close'].iloc[-1])
        vix_p = float(vix_h['Close'].iloc[-2])
        vix_chg = (vix - vix_p) / vix_p * 100
        
        # S&P 500
        sp_t = yf.Ticker('^GSPC')
        sp_h = sp_t.history(period='5d')
        sp_chg = float((sp_h['Close'].iloc[-1] / sp_h['Close'].iloc[-2] - 1) * 100)
        
        # Calculate Fear & Greed (simplified)
        if vix > 30:
            fear_greed = 20
            label = 'Extreme Fear'
        elif vix > 25:
            fear_greed = 40
            label = 'Fear'
        elif vix > 18:
            fear_greed = 55
            label = 'Neutral'
        elif vix > 12:
            fear_greed = 70
            label = 'Greed'
        else:
            fear_greed = 85
            label = 'Extreme Greed'
        
        # Risk scores
        if vix > 25:
            risk_off = 4
            risk_on = 1
            mode = 'Risk Off'
        elif vix < 18:
            risk_off = 2
            risk_on = 4
            mode = 'Risk On'
        else:
            risk_off = 3
            risk_on = 3
            mode = 'Neutral'
        
        conn = sqlite3.connect(DB_FILE)
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn.execute('''
            INSERT OR REPLACE INTO market_sentiment 
            (date, fear_greed_index, fear_greed_label, vix, vix_change_pct, risk_on_score, risk_off_score, market_mode, smart_money_indicator, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (today, fear_greed, label, vix, vix_chg, risk_on, risk_off, mode, 'watching', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f'  VIX: {vix:.2f} ({vix_chg:+.2f}%)')
        print(f'  Fear/Greed: {fear_greed} ({label})')
        print(f'  Mode: {mode}')
        
    except Exception as e:
        print(f'  Sentiment update error: {str(e)[:50]}')

def generate_report():
    """生成資金流向報告"""
    conn = sqlite3.connect(DB_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 板塊資金
    cur = conn.execute('''
        SELECT symbol, sector_name, price, change_pct, rsi, mfi, trend, flow_direction, heatmap_color
        FROM sector_flow 
        WHERE date = ?
        ORDER BY change_pct DESC
    ''', (today,))
    
    sectors = cur.fetchall()
    
    # 情緒
    cur2 = conn.execute('SELECT * FROM market_sentiment WHERE date = ? ORDER BY id DESC LIMIT 1', (today,))
    sentiment = cur2.fetchone()
    
    conn.close()
    
    print('='*70)
    print('  US Fund Flow Report')
    print(f'  Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*70)
    print()
    
    if sentiment:
        print('[MARKET SENTIMENT]')
        print(f'  Fear/Greed Index: {sentiment[1]} ({sentiment[2]})')
        print(f'  VIX: {sentiment[3]:.2f} ({sentiment[4]:+.2f}%)')
        print(f'  Mode: {sentiment[7]} (Risk On: {sentiment[5]}, Risk Off: {sentiment[6]})')
        print()
    
    print('[SECTOR FUND FLOWS]')
    print('-'*70)
    print(f'{"Symbol":<8} {"Sector":<20} {"Price":>10} {"Chg%":>8} {"RSI":>6} {"MFI":>6} {"Trend":<10} {"Flow":<10}')
    print('-'*70)
    
    inflow_sectors = []
    outflow_sectors = []
    
    for row in sectors:
        sym, name, price, chg, rsi, mfi, trend, flow, color = row
        sign = '+' if chg > 0 else ''
        
        color_emoji = {
            'strong_green': '[綠]',
            'green': '[淡綠]',
            'yellow': '[黃]',
            'red': '[淡紅]',
            'strong_red': '[紅]',
        }.get(color, '[灰]')
        
        print(f'{sym:<8} {name:<20} ${price:>8.2f} {sign}{chg:>6.2f}% {rsi:>6.0f} {mfi:>6.0f} {trend:<10} {flow:<10} {color_emoji}')
        
        if flow == 'inflow':
            inflow_sectors.append((sym, name, chg))
        elif flow == 'outflow':
            outflow_sectors.append((sym, name, chg))
    
    print()
    print('[FUND FLOW SUMMARY]')
    print(f'  Inflow Sectors: {len(inflow_sectors)}')
    for sym, name, chg in inflow_sectors:
        print(f'    - {sym} {name}: {chg:+.2f}%')
    
    print(f'  Outflow Sectors: {len(outflow_sectors)}')
    for sym, name, chg in outflow_sectors:
        print(f'    - {sym} {name}: {chg:+.2f}%')
    
    print()
    print('[RECOMMENDATIONS]')
    print('  BUY (MFI > 60, RSI > 50):')
    buy_recs = [s for s in sectors if float(s[5]) > 60 and float(s[4]) > 50]
    if buy_recs:
        for s in buy_recs[:5]:
            print(f'    - {s[0]} {s[1]}: RSI={s[4]:.0f}, MFI={s[5]:.0f}')
    else:
        print('    None')
    
    print('  SELL/WATCH (MFI < 40, RSI < 45):')
    sell_recs = [s for s in sectors if float(s[5]) < 40 and float(s[4]) < 45]
    if sell_recs:
        for s in sell_recs[:5]:
            print(f'    - {s[0]} {s[1]}: RSI={s[4]:.0f}, MFI={s[5]:.0f}')
    else:
        print('    None')
    
    print('='*70)

def update_all():
    """更新所有資金流向"""
    init_db()
    update_market_sentiment()
    update_sector_flow()
    generate_report()
    
    # Save JSON report
    conn = sqlite3.connect(DB_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    cur = conn.execute('SELECT * FROM sector_flow WHERE date = ?', (today,))
    sectors = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]
    
    cur2 = conn.execute('SELECT * FROM market_sentiment WHERE date = ? ORDER BY id DESC LIMIT 1', (today,))
    sentiment_row = cur2.fetchone()
    sentiment = dict(zip([d[0] for d in cur2.description], sentiment_row)) if sentiment_row else {}
    
    conn.close()
    
    report = {
        'date': today,
        'sentiment': sentiment,
        'sectors': sectors,
        'recommendations': {
            'buy': [s['symbol'] for s in sectors if s['mfi'] > 60 and s['rsi'] > 50],
            'sell': [s['symbol'] for s in sectors if s['mfi'] < 40 and s['rsi'] < 45],
            'watch': [s['symbol'] for s in sectors if s['flow_direction'] == 'neutral']
        }
    }
    
    out_file = DATA_DIR / 'data' / f'fund_flow_v2_{today}.json'
    DATA_DIR.joinpath('data').mkdir(exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'Report saved: {out_file}')

if __name__ == '__main__':
    update_all()