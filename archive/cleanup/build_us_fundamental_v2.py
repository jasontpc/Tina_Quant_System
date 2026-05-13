# -*- coding: utf-8 -*-
"""美股基本面資料庫 v2"""
import sys, sqlite3, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\us_fundamental_v2.db'

FIELDS = ['symbol','name','sector','price','div_yield','ann_div','payout','eps_ttm','eps_fwd','pe','fwd_pe','pb','mkt_cap','beta','revenue','rev_growth','earn_growth','profit_mgn','op_mgn','roe','roa','dte','curr_ratio','hi52','lo52','tgt_price','rec','updated']

def init():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cols = ','.join(FIELDS)
    cur.execute(f'CREATE TABLE fundamentals ({cols})')
    conn.commit()
    return conn

def fetch(sym, name):
    try:
        t = yfinance.Ticker(sym)
        i = t.info
        dy = i.get('dividendYield', 0) or 0
        if dy > 1: dy /= 100
        return [
            sym, name, i.get('sector',''),
            i.get('currentPrice',0) or i.get('regularMarketPrice',0),
            dy*100, i.get('annualDividendRate',0) or 0,
            i.get('payoutRatio',0) or 0,
            i.get('trailingEps',0) or 0,
            i.get('forwardEps',0) or 0,
            i.get('trailingPE',0) or 0,
            i.get('forwardPE',0) or 0,
            i.get('priceToBook',0) or 0,
            i.get('marketCap',0) or 0,
            i.get('beta',0) or 0,
            i.get('totalRevenue',0) or 0,
            i.get('revenueGrowth',0) or 0,
            i.get('earningsGrowth',0) or 0,
            i.get('profitMargins',0) or 0,
            i.get('operatingMargins',0) or 0,
            i.get('returnOnEquity',0) or 0,
            i.get('returnOnAssets',0) or 0,
            i.get('debtToEquity',0) or 0,
            i.get('currentRatio',0) or 0,
            i.get('fiftyTwoWeekHigh',0) or 0,
            i.get('fiftyTwoWeekLow',0) or 0,
            i.get('targetMeanPrice',0) or 0,
            i.get('recommendationKey','') or '',
            datetime.now().strftime('%Y-%m-%d')
        ]
    except:
        return None

def main():
    print('=== 美股基本面資料庫 v2 ===\n')
    conn = init()
    cur = conn.cursor()
    
    STOCKS = [
        ('AAPL','Apple'),('MSFT','Microsoft'),('GOOGL','Google'),
        ('AMZN','Amazon'),('META','Meta'),('NVDA','Nvidia'),
        ('TSLA','Tesla'),('AVGO','Broadcom'),('ORCL','Oracle'),
        ('AMD','AMD'),('INTC','Intel'),('QCOM','Qualcomm'),
        ('TXN','Texas'),('NOW','ServiceNow'),('SNOW','Snowflake'),
        ('CRWD','CrowdStrike'),('NET','Cloudflare'),('PLTR','Palantir'),
        ('JPM','JPMorgan'),('BAC','BofA'),('WFC','Wells Fargo'),
        ('GS','Goldman'),('BLK','BlackRock'),('SCHW','Schwab'),
        ('XOM','Exxon'),('CVX','Chevron'),('COP','Conoco'),
        ('UNH','UnitedHealth'),('JNJ','J&J'),('LLY','Eli Lilly'),
        ('PFE','Pfizer'),('ABBV','AbbVie'),('MRK','Merck'),
        ('TMO','Thermo'),('DHR','Danaher'),('AMGN','Amgen'),
        ('NKE','Nike'),('SBUX','Starbucks'),('MCD',"McDonald's"),
        ('KO','Coca-Cola'),('PEP','Pepsi'),('DIS','Disney'),
        ('CAT','Caterpillar'),('BA','Boeing'),('HON','Honeywell'),
        ('UNP','Union Pacific'),('DE','John Deere'),
        ('SPY','SPY'),('QQQ','QQQ'),('VGT','VGT'),
        ('XLE','XLE'),('XLV','XLV'),('XLF','XLF'),
        ('TQQQ','TQQQ'),('SPXL','SPXL'),
        ('GLD','GLD'),('SLV','SLV'),
    ]
    
    added = 0
    for sym, name in STOCKS:
        print(f'+ {sym}...', end='', flush=True)
        data = fetch(sym, name)
        if data:
            try:
                placeholders = ','.join(['?']*len(FIELDS))
                cur.execute(f'INSERT INTO fundamentals VALUES ({placeholders})', data)
                conn.commit()
                print(f' DY={data[4]:.1f}% EPS={data[7]:.2f} PE={data[9]:.1f}')
                added += 1
            except Exception as e:
                print(f' ERR: {e}')
        else:
            print(' ERR')
    
    conn.close()
    print(f'\n=== 完成: {added} 檔股票 ===')
    size = os.path.getsize(DB) / 1024
    print(f'資料庫: {DB}')
    print(f'大小: {size:.0f} KB')
    
    # Analyze
    conn2 = sqlite3.connect(DB)
    c2 = conn2.cursor()
    
    print('\n=== 殖利率 TOP 10 ===')
    c2.execute('SELECT symbol,name,div_yield,ann_div,pe FROM fundamentals WHERE div_yield>0 ORDER BY div_yield DESC LIMIT 10')
    for r in c2.fetchall():
        print(f'{r[0]:<8}{r[1]:<14}{r[2]:>5.2f}%  ${r[3]:.2f}/yr  PE:{r[4]:.1f}')
    
    print('\n=== EPS成長 TOP 10 ===')
    c2.execute('SELECT symbol,name,eps_ttm,eps_fwd,earn_growth FROM fundamentals WHERE eps_ttm>0 ORDER BY earn_growth DESC LIMIT 10')
    for r in c2.fetchall():
        eg = f'{r[4]*100:.1f}%' if r[4] else 'N/A'
        print(f'{r[0]:<8}{r[1]:<14}EPS=${r[2]:.2f}->${r[3]:.2f}  {eg}')
    
    print('\n=== 價值股：低PE + DY>2% ===')
    c2.execute('SELECT symbol,name,pe,div_yield FROM fundamentals WHERE pe>0 AND pe<20 AND div_yield>2 ORDER BY pe LIMIT 10')
    for r in c2.fetchall():
        print(f'{r[0]:<8}{r[1]:<14}PE:{r[2]:.1f}  DY:{r[3]:.2f}%')
    
    conn2.close()

if __name__ == '__main__':
    main()