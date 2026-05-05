"""
美股 AI/半導體/科技 季報資料庫
US AI/Semi/Tech Quarterly Financial Database

追蹤：營收、EPS、毛利率、營益率、淨利率
計算：YoY、MoM 成長率
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_financial.db'

# 美股 AI/半導體/科技 追蹤名單
STOCKS = {
    # AI/GPU
    'NVDA': {'name': 'Nvidia', 'sector': 'AI/GPU', 'industry': 'AI/HPC GPU'},
    'AMD': {'name': 'AMD', 'sector': 'AI/GPU', 'industry': 'AI/GPU'},
    'INTC': {'name': 'Intel', 'sector': 'AI/GPU', 'industry': 'AI/CPU'},
    'QCOM': {'name': 'Qualcomm', 'sector': 'AI/GPU', 'industry': 'AI/手機晶片'},
    
    # 雲端/AI 服務
    'MSFT': {'name': 'Microsoft', 'sector': 'Cloud/AI', 'industry': 'AI/Azure'},
    'GOOGL': {'name': 'Alphabet', 'sector': 'Cloud/AI', 'industry': 'AI/雲端'},
    'AMZN': {'name': 'Amazon', 'sector': 'Cloud/AI', 'industry': 'AI/AWS'},
    'META': {'name': 'Meta', 'sector': 'Cloud/AI', 'industry': 'AI/社群'},
    
    # AI 應用
    'PLTR': {'name': 'Palantir', 'sector': 'AI/應用', 'industry': 'AI/資料分析'},
    'SNOW': {'name': 'Snowflake', 'sector': 'AI/應用', 'industry': 'AI/數據雲'},
    'AI': {'name': 'C3.ai', 'sector': 'AI/應用', 'industry': 'AI/企業軟體'},
    'PATH': {'name': 'UiPath', 'sector': 'AI/應用', 'industry': 'AI/RPA'},
    
    # 半導體設備
    'TSM': {'name': '台積電ADR', 'sector': '半導體', 'industry': 'AI/晶圓製造'},
    'ASML': {'name': 'ASML', 'sector': '半導體', 'industry': 'AI/半導體設備'},
    'AMAT': {'name': 'Applied Materials', 'sector': '半導體', 'industry': 'AI/半導體設備'},
    'LRCX': {'name': 'Lam Research', 'sector': '半導體', 'industry': 'AI/半導體設備'},
    
    # 高速運算/網路
    'NVTS': {'name': 'Navitas', 'sector': 'AI/功率', 'industry': 'AI/功率半導體'},
    'MRVL': {'name': 'Marvell', 'sector': 'AI/網路', 'industry': 'AI/資料中心網路'},
    'CDNS': {'name': 'Cadence', 'sector': 'AI/IC設計', 'industry': 'AI/EDA軟體'},
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
        industry TEXT,
        created_at TEXT
    )
    ''')
    
    # 營收數據
    cur.execute('''
    CREATE TABLE IF NOT EXISTS revenue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        quarter TEXT,
        revenue REAL,
        revenue_yoy REAL,
        revenue_mom REAL
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue ON revenue(symbol, quarter)')
    
    # 獲利能力
    cur.execute('''
    CREATE TABLE IF NOT EXISTS profitability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        quarter TEXT,
        gross_margin REAL,
        operating_margin REAL,
        net_margin REAL,
        eps REAL
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_profitability ON profitability(symbol, quarter)')
    
    # 評估分數
    cur.execute('''
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        quarter TEXT,
        revenue_score REAL,
        profitability_score REAL,
        growth_score REAL,
        overall_score REAL,
        recommendation TEXT
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_scores ON scores(symbol, quarter)')
    
    conn.commit()
    
    # 初始化股票池
    for sym, info in STOCKS.items():
        cur.execute('''
            INSERT OR IGNORE INTO stocks (symbol, name, sector, industry, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], info['industry'], datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f'Database initialized: {DB_FILE}')

def get_quarter_str(idx, total_cols):
    """從索引計算季度字串"""
    current_year = datetime.now().year
    quarters_back = (total_cols - 1 - idx) // 1
    q_year = current_year - (quarters_back // 4)
    q_num = ((quarters_back % 4) + 1)
    return f'{q_year}Q{q_num}'

def fetch_financial_data(symbol):
    """從 Yahoo Finance 抓取財務數據"""
    try:
        ticker = yf.Ticker(symbol)
        fin = ticker.financials
        
        if fin.empty or len(fin.columns) == 0:
            return None
        
        total_cols = len(fin.columns)
        data = {}
        
        for i in range(min(8, total_cols)):
            q = fin.columns[i]
            q_str = get_quarter_str(i, total_cols)
            
            # 營收
            try:
                revenue = fin.iloc[fin.index.get_loc('Total Revenue'), i] if 'Total Revenue' in fin.index else None
            except:
                revenue = None
            
            # 毛利
            try:
                gross_profit = fin.iloc[fin.index.get_loc('Gross Profit'), i] if 'Gross Profit' in fin.index else None
            except:
                gross_profit = None
            
            # 營益
            try:
                operating_income = fin.iloc[fin.index.get_loc('Operating Income'), i] if 'Operating Income' in fin.index else None
            except:
                operating_income = None
            
            # 淨利
            try:
                net_income = fin.iloc[fin.index.get_loc('Net Income'), i] if 'Net Income' in fin.index else None
            except:
                net_income = None
            
            # EPS
            try:
                eps = fin.iloc[fin.index.get_loc('Basic EPS'), i] if 'Basic EPS' in fin.index else None
            except:
                eps = None
            
            # 計算比率
            gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit and revenue != 0 else None
            operating_margin = (operating_income / revenue * 100) if revenue and operating_income and revenue != 0 else None
            net_margin = (net_income / revenue * 100) if revenue and net_income and revenue != 0 else None
            
            # 營收轉換為億美元
            if revenue:
                revenue = revenue / 1e9
            
            data[q_str] = {
                'revenue': revenue,
                'gross_margin': gross_margin,
                'operating_margin': operating_margin,
                'net_margin': net_margin,
                'eps': eps,
            }
        
        return data
        
    except Exception as e:
        print(f'Error fetching {symbol}: {str(e)[:50]}')
        return None

def update_all():
    """更新所有資料"""
    print('Updating US AI/Semi/Tech Financial Database...')
    conn = sqlite3.connect(DB_FILE)
    updated = 0
    
    for sym in STOCKS.keys():
        try:
            data = fetch_financial_data(sym)
            if not data:
                print(f'  {sym}: No data')
                continue
            
            quarters = list(data.keys())
            
            for i, q_str in enumerate(quarters):
                d = data[q_str]
                
                if d['revenue'] is None:
                    continue
                
                # YoY 計算
                if i >= 4 and quarters[i-4] in data:
                    prev_rev = data[quarters[i-4]]['revenue']
                    if prev_rev and prev_rev != 0:
                        yoy = ((d['revenue'] - prev_rev) / abs(prev_rev)) * 100
                    else:
                        yoy = None
                else:
                    yoy = None
                
                # MoM 計算
                if i > 0 and quarters[i-1] in data:
                    prev_rev = data[quarters[i-1]]['revenue']
                    if prev_rev and prev_rev != 0:
                        mom = ((d['revenue'] - prev_rev) / abs(prev_rev)) * 100
                    else:
                        mom = None
                else:
                    mom = None
                
                # 寫入
                conn.execute('''
                    INSERT OR REPLACE INTO revenue 
                    (symbol, quarter, revenue, revenue_yoy, revenue_mom)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sym, q_str, d['revenue'], yoy, mom))
                
                conn.execute('''
                    INSERT OR REPLACE INTO profitability
                    (symbol, quarter, gross_margin, operating_margin, net_margin, eps)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (sym, q_str, d['gross_margin'], d['operating_margin'], d['net_margin'], d['eps']))
            
            # 計算分數
            latest_q = quarters[-1] if quarters else None
            if latest_q and latest_q in data:
                d = data[latest_q]
                score = calc_score(d)
                
                conn.execute('''
                    INSERT OR REPLACE INTO scores
                    (symbol, quarter, revenue_score, profitability_score, growth_score, overall_score, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (sym, latest_q, score['revenue'], score['profitability'], score['growth'], 
                      score['overall'], score['recommendation']))
            
            updated += 1
            print(f'  {sym} {STOCKS[sym]["name"]} OK ({updated}/{len(STOCKS)})')
            
        except Exception as e:
            print(f'  {sym}: {str(e)[:50]}')
    
    conn.commit()
    conn.close()
    print(f'\nUpdated: {updated} stocks')
    return {'updated': updated}

def calc_score(data):
    """計算評估分數"""
    score = {'revenue': 50, 'profitability': 50, 'growth': 50, 'overall': 50, 'recommendation': 'HOLD'}
    
    # 毛利率分數
    if data.get('gross_margin'):
        gm = data['gross_margin']
        if gm > 60: score['profitability'] = 95
        elif gm > 50: score['profitability'] = 80
        elif gm > 40: score['profitability'] = 65
        elif gm > 30: score['profitability'] = 50
        else: score['profitability'] = 40
    
    # 營益率加分
    if data.get('operating_margin'):
        om = data['operating_margin']
        if om > 30: score['profitability'] += 10
        elif om > 20: score['profitability'] += 5
    
    # 成長動能
    score['growth'] = (score['revenue'] + score['profitability']) / 2
    score['overall'] = (score['revenue'] * 0.3 + score['profitability'] * 0.4 + score['growth'] * 0.3)
    
    # 推薦
    if score['overall'] >= 75: score['recommendation'] = 'BUY'
    elif score['overall'] < 45: score['recommendation'] = 'SELL'
    
    return score

def get_report():
    """生成季報分析報告"""
    conn = sqlite3.connect(DB_FILE)
    
    cur = conn.execute('''
        SELECT s.symbol, st.name, s.quarter, s.overall_score, s.recommendation,
               r.revenue, r.revenue_yoy,
               p.gross_margin, p.operating_margin, p.net_margin, p.eps
        FROM scores s
        JOIN stocks st ON s.symbol = st.symbol
        LEFT JOIN revenue r ON s.symbol = r.symbol AND s.quarter = r.quarter
        LEFT JOIN profitability p ON s.symbol = p.symbol AND s.quarter = p.quarter
        ORDER BY s.overall_score DESC
    ''')
    
    rows = cur.fetchall()
    conn.close()
    return rows

def print_report():
    """輸出季報報告"""
    rows = get_report()
    
    print('='*90)
    print('  US AI/Semi/Tech Quarterly Report (2026-04-29)')
    print('='*90)
    print()
    
    print(f"{'Symbol':<8} {'Name':<12} {'Score':<6} {'Reco':<7} {'Revenue(B)':<12} {'YoY%':<8} {'GM%':<8} {'OM%':<8} {'NM%':<8} {'EPS':<8}")
    print('-'*90)
    
    for row in rows:
        sym, name, q, score, reco, rev, rev_yoy, gm, om, nm, eps = row
        score_str = f'{score:.1f}' if score else '-'
        rev_str = f'${rev:.1f}B' if rev else '-'
        yoy_str = f'{rev_yoy:+.1f}%' if rev_yoy else '-'
        gm_str = f'{gm:.1f}%' if gm else '-'
        om_str = f'{om:.1f}%' if om else '-'
        nm_str = f'{nm:.1f}%' if nm else '-'
        eps_str = f'${eps:.2f}' if eps else '-'
        reco_str = f'[{reco}]' if reco else '-'
        
        print(f'{sym:<8} {name:<12} {score_str:<6} {reco_str:<7} {rev_str:<12} {yoy_str:<8} {gm_str:<8} {om_str:<8} {nm_str:<8} {eps_str:<8}')
    
    print()
    
    buys = [r for r in rows if r[4] == 'BUY']
    holds = [r for r in rows if r[4] == 'HOLD']
    sells = [r for r in rows if r[4] == 'SELL']
    
    print(f'[Summary] BUY: {len(buys)} | HOLD: {len(holds)} | SELL: {len(sells)}')
    print('='*90)

if __name__ == '__main__':
    init_db()
    result = update_all()
    print_report()
    
    out_file = DATA_DIR / f'financial_report_{datetime.now().strftime("%Y%m%d")}.json'
    rows = get_report()
    report_data = []
    for row in rows:
        report_data.append({
            'symbol': row[0],
            'name': row[1],
            'quarter': row[2],
            'score': row[3],
            'recommendation': row[4],
            'revenue': row[5],
            'rev_yoy': row[6],
            'gross_margin': row[7],
            'operating_margin': row[8],
            'net_margin': row[9],
            'eps': row[10],
        })
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'stocks': report_data}, f, ensure_ascii=False, indent=2)
    print(f'\nReport saved: {out_file}')