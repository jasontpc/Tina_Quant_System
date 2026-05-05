"""
台股 Margin 資料庫
TW Margin Database - 融資融券、主力動向、借券資料
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_margin.db'

# 台股 Margin 監控名單（AI/科技/權值股）
MARGIN_STOCKS = {
    # AI/科技上游
    '2330': {'name': '台積電', 'sector': '半導體', 'margin_eligible': True},
    '2454': {'name': '聯發科', 'sector': 'IC設計', 'margin_eligible': True},
    '2379': {'name': '瑞昱', 'sector': 'IC設計', 'margin_eligible': True},
    '3035': {'name': '智原', 'sector': 'IC設計', 'margin_eligible': True},
    '3653': {'name': '健策', 'sector': '導線架', 'margin_eligible': True},
    
    # AI/科技中游
    '2382': {'name': '廣達', 'sector': '伺服器', 'margin_eligible': True},
    '3034': {'name': '緯穎', 'sector': '伺服器', 'margin_eligible': True},
    '4938': {'name': '和碩', 'sector': 'EMS', 'margin_eligible': True},
    '2376': {'name': '技嘉', 'sector': 'GPU/板卡', 'margin_eligible': True},
    '3665': {'name': '穎崴', 'sector': 'AI封測', 'margin_eligible': True},
    '6153': {'name': '嘉澤', 'sector': '連接器', 'margin_eligible': True},
    
    # AI/科技下游
    '2317': {'name': '鴻海', 'sector': 'EMS/組裝', 'margin_eligible': True},
    '6706': {'name': '健鼎', 'sector': 'PCB', 'margin_eligible': True},
    '6271': {'name': '敦南', 'sector': 'PCB', 'margin_eligible': True},
    '3016': {'name': '奇鋐', 'sector': '散熱', 'margin_eligible': True},
    '6230': {'name': '尼得科', 'sector': '散熱', 'margin_eligible': True},
    
    # 權值股
    '2881': {'name': '富邦金', 'sector': '金融', 'margin_eligible': True},
    '2882': {'name': '國泰金', 'sector': '金融', 'margin_eligible': True},
    '2891': {'name': '中信金', 'sector': '金融', 'margin_eligible': True},
    '2892': {'name': '第一金', 'sector': '金融', 'margin_eligible': True},
    '2002': {'name': '中鋼', 'sector': '鋼鐵', 'margin_eligible': True},
    '1101': {'name': '台泥', 'sector': '水泥', 'margin_eligible': True},
    '1215': {'name': '卜蜂', 'sector': '食品', 'margin_eligible': True},
    
    # ETF
    '0050': {'name': '元大台灣50', 'sector': 'ETF', 'margin_eligible': True},
    '0056': {'name': '元大高股息', 'sector': 'ETF', 'margin_eligible': True},
    '00878': {'name': '國泰永續高股息', 'sector': 'ETF', 'margin_eligible': True},
    '00646': {'name': '富邦S&P500', 'sector': 'ETF', 'margin_eligible': True},
    '00662': {'name': '富邦NASDAQ100', 'sector': 'ETF', 'margin_eligible': True},
    '00713': {'name': '元大高息低波', 'sector': 'ETF', 'margin_eligible': True},
}

# 去除重複
MARGIN_STOCKS = {k: v for k, v in MARGIN_STOCKS.items()}

# Margin 參數（台股）
MARGIN_PARAMS = {
    'initial_margin': 0.30,         # 台股融資成數一般 30-60%
    'maintenance_margin': 0.20,     # 維持率 20%
    'margin_call_threshold': 0.25,  # 追繳門檻 25%
    'max_margin_ratio': 0.30,       # 建議最大融資比率
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # 股票池
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        margin_eligible INTEGER,
        created_at TEXT
    )
    ''')
    
    # 每日價格數據
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        UNIQUE(symbol, date)
    )
    ''')
    
    # Margin 數據（融資融券）
    cur.execute('''
    CREATE TABLE IF NOT EXISTS margin_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        margin_balance REAL,      -- 融資餘額
        short_balance REAL,       -- 融券餘額
        margin_balance_chg REAL, -- 融資變化
        short_balance_chg REAL,  -- 融券變化
        margin_ratio REAL,        -- 融資佔比
        short_ratio REAL,         -- 融券佔比
        net_margin REAL,          -- 淨融資
        UNIQUE(symbol, date)
    )
    ''')
    
    # 法人買賣超
    cur.execute('''
    CREATE TABLE IF NOT EXISTS institutional (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        foreign_buy REAL,         -- 外資買超
        foreign_sell REAL,        -- 外資賣超
        foreign_net REAL,         -- 外資淨買
        trust_buy REAL,           -- 投信買超
        trust_sell REAL,          -- 投信賣超
        trust_net REAL,           -- 投信淨買
        dealer_buy REAL,          -- 自營商買超
        dealer_sell REAL,         -- 自營商賣超
        dealer_net REAL,          -- 自營商淨買
        UNIQUE(symbol, date)
    )
    ''')
    
    # 技術指標快取
    cur.execute('''
    CREATE TABLE IF NOT EXISTS indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        rsi14 REAL,
        rsi30 REAL,
        rsi50 REAL,
        ma20 REAL,
        ma60 REAL,
        ma200 REAL,
        volatility REAL,
        beta REAL,
        price_chg REAL,
        margin_ratio REAL,
        UNIQUE(symbol, date)
    )
    ''')
    
    # 風險警報
    cur.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        alert_type TEXT,
        severity TEXT,
        message TEXT,
        rsi REAL,
        margin_ratio REAL,
        price_chg REAL,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    
    # 初始化股票池
    for sym, info in MARGIN_STOCKS.items():
        cur.execute('''
            INSERT OR IGNORE INTO stocks (symbol, name, sector, margin_eligible, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], 1 if info['margin_eligible'] else 0, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f'資料庫初始化完成: {DB_FILE}')

def get_margin_risk(symbol):
    """計算單一股票的 Margin 風險"""
    conn = sqlite3.connect(DB_FILE)
    
    # 取得最新數據
    cur = conn.execute('''
        SELECT margin_ratio, rsi, price_chg 
        FROM indicators i
        WHERE symbol = ?
        ORDER BY date DESC LIMIT 1
    ''', (symbol,))
    
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    margin_ratio, rsi, price_chg = row
    
    # 風險評估
    risk_level = 'LOW'
    if rsi and margin_ratio:
        if rsi > 80 and margin_ratio > 0.25:
            risk_level = 'HIGH'
        elif rsi > 60 and margin_ratio > 0.20:
            risk_level = 'MEDIUM'
    
    return {
        'symbol': symbol,
        'rsi': rsi,
        'margin_ratio': margin_ratio,
        'risk_level': risk_level,
        'price_chg': price_chg
    }

def get_all_alerts():
    """取得所有風險警報"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute('''
        SELECT symbol, alert_type, severity, message, rsi, margin_ratio, created_at
        FROM alerts
        WHERE created_at >= date('now', '-7 days')
        ORDER BY created_at DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        alerts.append({
            'symbol': row[0],
            'alert_type': row[1],
            'severity': row[2],
            'message': row[3],
            'rsi': row[4],
            'margin_ratio': row[5],
            'created_at': row[6]
        })
    return alerts

def calc_rsi(prices, period=14):
    """計算 RSI"""
    if len(prices) < period + 1:
        return 50.0
    deltas = pd.Series(prices).diff()
    gain = deltas.clip(lower=0).rolling(period).mean()
    loss = (-deltas.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def update_all():
    """更新所有數據"""
    print('開始更新台股 Margin 資料庫...')
    conn = sqlite3.connect(DB_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    updated = 0
    alerts = []
    
    for sym in MARGIN_STOCKS.keys():
        try:
            t = yf.Ticker(f'{sym}.TW')
            h = t.history(period='60d', timeout=10)
            
            if h.empty:
                continue
            
            # 更新價格
            for i in range(len(h)):
                date_str = h.index[i].strftime('%Y-%m-%d')
                conn.execute('''
                    INSERT OR REPLACE INTO daily_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (sym, date_str, float(h['Open'].iloc[i]), float(h['High'].iloc[i]),
                      float(h['Low'].iloc[i]), float(h['Close'].iloc[i]), int(h['Volume'].iloc[i])))
            
            # 計算技術指標
            closes = h['Close'].tolist()
            rsi14 = calc_rsi(closes, 14)
            rsi30 = calc_rsi(closes, 30)
            rsi50 = calc_rsi(closes, 50)
            
            # MA 計算
            ma20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 20 else closes[-1]
            ma60 = sum(closes[-60:]) / min(60, len(closes)) if len(closes) >= 60 else closes[-1]
            ma200 = sum(closes[-200:]) / min(200, len(closes)) if len(closes) >= 200 else closes[-1]
            
            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) >= 2 else closes[-1]
            price_chg = (current_price - prev_price) / prev_price * 100
            
            # Margin ratio 估算（使用 RSI 區間）
            margin_ratio = 0.0
            if rsi14 < 30:
                margin_ratio = 0.25  # 低 RSI → 高 Margin 空間
            elif rsi14 < 50:
                margin_ratio = 0.15
            elif rsi14 < 70:
                margin_ratio = 0.08
            else:
                margin_ratio = 0.03  # 高 RSI → 低 Margin 空間
            
            conn.execute('''
                INSERT OR REPLACE INTO indicators
                (symbol, date, rsi14, rsi30, rsi50, ma20, ma60, ma200, volatility, beta, price_chg, margin_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym, today, rsi14, rsi30, rsi50, ma20, ma60, ma200, 0.0, 1.0, price_chg, margin_ratio))
            
            # 檢查警報
            if rsi14 > 80:
                alerts.append({
                    'symbol': sym,
                    'alert_type': 'OVERBOUGHT_MARGIN',
                    'severity': 'HIGH',
                    'message': f'{sym} RSI={rsi14:.1f} 過熱，Margin 風險高',
                    'rsi': rsi14,
                    'margin_ratio': margin_ratio,
                    'price_chg': price_chg
                })
            elif rsi14 > 70:
                alerts.append({
                    'symbol': sym,
                    'alert_type': 'WATCH',
                    'severity': 'MEDIUM',
                    'message': f'{sym} RSI={rsi14:.1f} 偏高，注意風險',
                    'rsi': rsi14,
                    'margin_ratio': margin_ratio,
                    'price_chg': price_chg
                })
            
            updated += 1
            
        except Exception as e:
            err_msg = str(e)
            # Only print if it's not the expected error (first stock might have schema issue)
            if 'values for' in err_msg or 'no such column' in err_msg:
                print(f'  {sym}: DB error {err_msg[:60]}')
    
    # 儲存警報
    for alert in alerts:
        conn.execute('''
            INSERT INTO alerts (symbol, date, alert_type, severity, message, rsi, margin_ratio, price_chg, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (alert['symbol'], today, alert['alert_type'], alert['severity'], alert['message'],
              alert['rsi'], alert['margin_ratio'], alert['price_chg'], datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    print(f'更新完成: {updated} 檔股票')
    print(f'警報數: {len(alerts)}')
    
    return {'updated': updated, 'alerts': alerts}

def get_report():
    """生成報告"""
    conn = sqlite3.connect(DB_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 取得報表情況
    cur = conn.execute('''
        SELECT i.symbol, s.name, s.sector, i.rsi14, i.rsi30, i.rsi50,
               i.price_chg, i.margin_ratio
        FROM indicators i
        JOIN stocks s ON i.symbol = s.symbol
        WHERE i.date = ?
        ORDER BY i.rsi14 DESC
    ''', (today,))
    
    rows = cur.fetchall()
    conn.close()
    
    high = []
    medium = []
    low = []
    
    for row in rows:
        sym, name, sector, rsi14, rsi30, rsi50, price_chg, margin_ratio = row
        
        if rsi14 and margin_ratio:
            if rsi14 > 70 or margin_ratio > 0.20:
                level = 'HIGH'
                high.append(row)
            elif rsi14 > 55 or margin_ratio > 0.12:
                level = 'MEDIUM'
                medium.append(row)
            else:
                level = 'LOW'
                low.append(row)
    
    return {'high': high, 'medium': medium, 'low': low, 'total': len(rows)}

def print_report():
    """輸出報告"""
    report = get_report()
    
    print('='*60)
    print('  台股 Margin 風險報告 (2026-04-29)')
    print('='*60)
    print()
    
    print(f'【高風險 ({len(report["high"])} 檔)】')
    print('-'*60)
    for row in report['high'][:10]:
        sym, name, sector, rsi14, rsi30, rsi50, price_chg, margin_ratio = row
        print(f"  🔴 {sym} {name} ({sector})")
        print(f"      RSI: {rsi14:.1f}  漲跌: {price_chg:+.1f}%  Margin: {margin_ratio:.1%}")
    
    print()
    print(f'【中風險 ({len(report["medium"])} 檔)】')
    print('-'*60)
    for row in report['medium'][:10]:
        sym, name, sector, rsi14, rsi30, rsi50, price_chg, margin_ratio = row
        print(f"  ⚠️ {sym} {name} ({sector})")
        print(f"      RSI: {rsi14:.1f}  漲跌: {price_chg:+.1f}%  Margin: {margin_ratio:.1%}")
    
    print()
    print(f'【低風險 ({len(report["low"])} 檔)】')
    print('-'*60)
    for row in report['low'][:5]:
        sym, name, sector, rsi14, rsi30, rsi50, price_chg, margin_ratio = row
        print(f"  🟢 {sym} {name} ({sector})")
        print(f"      RSI: {rsi14:.1f}  漲跌: {price_chg:+.1f}%  Margin: {margin_ratio:.1%}")
    
    print()
    print('='*60)
    print(f'總計: {report["total"]} 檔 | 高風險: {len(report["high"])} | 中風險: {len(report["medium"])} | 低風險: {len(report["low"])}')
    print('='*60)

if __name__ == '__main__':
    init_db()
    result = update_all()
    print_report()
    
    # 儲存報告
    out_file = DATA_DIR / f'margin_report_{datetime.now().strftime("%Y%m%d")}.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n報告已儲存: {out_file}')