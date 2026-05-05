"""
台股 AI/半導體/科技 季報資料庫
Taiwan AI/Semi/Tech Quarterly Financial Database

追蹤：營收、EPS、毛利率、營益率、淨利率
計算：YoY、MoM 成長率
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_financial.db'

# AI/半導體/科技 追蹤名單
STOCKS = {
    # 上游 - 半導體/IC設計
    '2330': {'name': '台積電', 'sector': '半導體', 'industry': '晶圓製造'},
    '2454': {'name': '聯發科', 'sector': 'IC設計', 'industry': '手機/AI IC'},
    '2379': {'name': '瑞昱', 'sector': 'IC設計', 'industry': '網通IC'},
    '3035': {'name': '智原', 'sector': 'IC設計', 'industry': 'AI ASIC'},
    '3653': {'name': '健策', 'sector': '半導體', 'industry': '導線架'},
    '3189': {'name': '景碩', 'sector': '半導體', 'industry': 'ABF載板'},
    
    # 中游 - 伺服器/封測
    '2382': {'name': '廣達', 'sector': '伺服器', 'industry': 'AI伺服器'},
    '3034': {'name': '緯穎', 'sector': '伺服器', 'industry': 'AI伺服器'},
    '3665': {'name': '穎崴', 'sector': '封測', 'industry': 'AI封測'},
    '2376': {'name': '技嘉', 'sector': '板卡', 'industry': 'GPU伺服器'},
    '5269': {'name': '祥碩', 'sector': 'IC設計', 'industry': '高速傳輸'},
    '6153': {'name': '嘉澤', 'sector': '零組件', 'industry': '連接器'},
    
    # 下游 - EMS/PCB/散熱
    '2317': {'name': '鴻海', 'sector': 'EMS', 'industry': 'AI伺服器'},
    '6706': {'name': '健鼎', 'sector': 'PCB', 'industry': 'AI PCB'},
    '3016': {'name': '奇鋐', 'sector': '散熱', 'industry': 'AI散熱'},
    '4566': {'name': '研華', 'sector': '工業電腦', 'industry': 'AI Edge'},
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
    print(f'資料庫初始化完成: {DB_FILE}')

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
        ticker = yf.Ticker(f'{symbol}.TW')
        fin = ticker.financials
        
        if fin.empty or len(fin.columns) == 0:
            return None
        
        total_cols = len(fin.columns)
        data = {}
        
        for i in range(min(8, total_cols)):  # 最多8列
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
            
            # 計算毛利率
            if revenue and gross_profit and revenue != 0:
                gross_margin = (gross_profit / revenue) * 100
            else:
                gross_margin = None
            
            # 營益率
            if revenue and operating_income and revenue != 0:
                operating_margin = (operating_income / revenue) * 100
            else:
                operating_margin = None
            
            # 淨利率
            if revenue and net_income and revenue != 0:
                net_margin = (net_income / revenue) * 100
            else:
                net_margin = None
            
            # 轉換營收為億元
            if revenue:
                revenue = revenue / 1e8
            
            data[q_str] = {
                'revenue': revenue,
                'gross_margin': gross_margin,
                'operating_margin': operating_margin,
                'net_margin': net_margin,
            }
        
        return data
        
    except Exception as e:
        print(f'Error fetching {symbol}: {str(e)[:50]}')
        return None

def update_all():
    """更新所有資料"""
    print('開始更新台股 AI/半導體/科技 季報資料庫...')
    conn = sqlite3.connect(DB_FILE)
    updated = 0
    
    for sym in STOCKS.keys():
        try:
            data = fetch_financial_data(sym)
            if not data:
                continue
            
            quarters = list(data.keys())
            
            for i, q_str in enumerate(quarters):
                d = data[q_str]
                
                if d['revenue'] is None:
                    continue
                
                # YoY 計算（落後4期）
                if i >= 4 and quarters[i-4] in data:
                    prev_rev = data[quarters[i-4]]['revenue']
                    if prev_rev and prev_rev != 0:
                        yoy = ((d['revenue'] - prev_rev) / abs(prev_rev)) * 100
                    else:
                        yoy = None
                else:
                    yoy = None
                
                # MoM 計算（前一期）
                if i > 0 and quarters[i-1] in data:
                    prev_rev = data[quarters[i-1]]['revenue']
                    if prev_rev and prev_rev != 0:
                        mom = ((d['revenue'] - prev_rev) / abs(prev_rev)) * 100
                    else:
                        mom = None
                else:
                    mom = None
                
                # 寫入 revenue
                conn.execute('''
                    INSERT OR REPLACE INTO revenue 
                    (symbol, quarter, revenue, revenue_yoy, revenue_mom)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sym, q_str, d['revenue'], yoy, mom))
                
                # 寫入 profitability
                conn.execute('''
                    INSERT OR REPLACE INTO profitability
                    (symbol, quarter, gross_margin, operating_margin, net_margin)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sym, q_str, d['gross_margin'], d['operating_margin'], d['net_margin']))
            
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
            print(f'  {sym} {STOCKS[sym]["name"]} 更新成功 ({updated}/{len(STOCKS)})')
            
        except Exception as e:
            print(f'  {sym}: {str(e)[:50]}')
    
    conn.commit()
    conn.close()
    print(f'\n更新完成: {updated} 檔股票')
    return {'updated': updated}

def calc_score(data):
    """計算評估分數"""
    score = {'revenue': 50, 'profitability': 50, 'growth': 50, 'overall': 50, 'recommendation': 'HOLD'}
    
    # 毛利率分數
    if data.get('gross_margin'):
        gm = data['gross_margin']
        if gm > 50: score['profitability'] = 90
        elif gm > 40: score['profitability'] = 75
        elif gm > 30: score['profitability'] = 60
        else: score['profitability'] = 45
    
    # 營益率加分
    if data.get('operating_margin'):
        om = data['operating_margin']
        if om > 25: score['profitability'] += 10
        elif om > 15: score['profitability'] += 5
    
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
               p.gross_margin, p.operating_margin, p.net_margin
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
    
    print('='*85)
    print('  台股 AI/半導體/科技 季報分析 (2026-04-29)')
    print('='*85)
    print()
    
    print(f"{'股票':<6} {'名稱':<8} {'分數':<6} {'建議':<6} {'營收(億)':<10} {'YoY%':<8} {'毛利率':<8} {'營益率':<8} {'淨利率':<8}")
    print('-'*85)
    
    for row in rows:
        sym, name, q, score, reco, rev, rev_yoy, gm, om, nm = row
        score_str = f'{score:.1f}' if score else '-'
        rev_str = f'{rev:.1f}' if rev else '-'
        yoy_str = f'{rev_yoy:+.1f}%' if rev_yoy else '-'
        gm_str = f'{gm:.1f}%' if gm else '-'
        om_str = f'{om:.1f}%' if om else '-'
        nm_str = f'{nm:.1f}%' if nm else '-'
        
        reco_str = f'[{reco}]' if reco else '-'
        
        print(f'{sym:<6} {name:<8} {score_str:<6} {reco_str:<7} {rev_str:<10} {yoy_str:<8} {gm_str:<8} {om_str:<8} {nm_str:<8}')
    
    print()
    
    buys = [r for r in rows if r[4] == 'BUY']
    holds = [r for r in rows if r[4] == 'HOLD']
    sells = [r for r in rows if r[4] == 'SELL']
    
    print(f'【Summary】BUY: {len(buys)} | HOLD: {len(holds)} | SELL: {len(sells)}')
    print('='*85)

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
        })
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'stocks': report_data}, f, ensure_ascii=False, indent=2)
    print(f'\n報告已儲存: {out_file}')