# -*- coding: utf-8 -*-
"""
Nana v1.0 Hybrid Data Fetcher
==============================
yfinance (股價) + TWSE (法人) 混合抓取
自動對齊資料並計算 Nana 評分所需指標

功能:
1. yfinance 股價抓取 (還原股價)
2. TWSE 法人籌碼資料 (with 防爬蟲)
3. 民國年轉西元年
4. 資料對齊 (Data Join)
5. 技術指標計算 (RSI, MA, Bias)
6. 法人連續買超天數計算
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import sqlite3
import time
from datetime import datetime, timedelta
from io import StringIO

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== TWSE API 爬蟲 ====================

def get_twse_institutional(date_str):
    """
    從 TWSE 抓取三大法人買賣超 (單日)
    date_str: '2026-04-23'
    """
    # 民國年轉換
    year, month, day = date_str.split('-')
    roc_year = str(int(year) - 1911)
    date_roc = f'{roc_year}/{month}/{day}'
    
    # TWSE API
    url = 'https://www.twse.com.tw/rwd/zh/fund/T86'
    params = {
        'date': date_roc,
        'selectType': 'ALL',
        'response': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'])
            df.columns = ['Code', 'Name', 'Foreign_Buy', 'Foreign_Sell', 
                         'Trust_Buy', 'Trust_Sell', 'Foreign_Net', 'Trust_Net']
            
            # 轉換數值
            for col in ['Foreign_Buy', 'Foreign_Sell', 'Trust_Buy', 'Trust_Sell', 
                       'Foreign_Net', 'Trust_Net']:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            return df
        else:
            return None
    
    except Exception as e:
        print(f' TWSE API 錯誤: {e}')
        return None

def batch_get_twse_institutional(start_date, end_date):
    """
    批次抓取 TWSE 法人數據 (含防爬蟲延遲)
    注意: 建議一次抓取後存到 SQLite，不要每次回測都重新抓
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_data = []
    current = start_dt
    
    while current <= end_dt:
        date_str = current.strftime('%Y-%m-%d')
        
        df = get_twse_institutional(date_str)
        
        if df is not None and len(df) > 0:
            df['Date'] = date_str
            all_data.append(df)
            print(f'  {date_str}: {len(df)} 筆')
        
        time.sleep(5)  # 防爬蟲: 每5秒請求一次
        current += timedelta(days=1)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None

# ==================== yfinance 股價抓取 ====================

def get_stock_price_yfinance(stock_id, start_date, end_date):
    """
    使用 yfinance 抓取還原股價
    上市: .TW, 上櫃: .TWO
    """
    # 判斷上市/上櫃 (簡化: 通常 4位數且 > 5000 是上市)
    try:
        code = int(stock_id)
        if code >= 5000:
            suffix = '.TW'
        else:
            suffix = '.TW'  # 預設上市
    except:
        suffix = '.TW'
    
    ticker = f'{stock_id}{suffix}'
    
    try:
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
        
        if df is None or len(df) == 0:
            return None
        
        # 處理 MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        # 轉換索引
        df = df.reset_index()
        
        # 統一列名為小寫
        df.columns = [str(c).lower() for c in df.columns]
        
        # 確保有 date/datetime 列
        date_col = None
        for c in df.columns:
            if 'date' in str(c).lower() or 'datetime' in str(c).lower():
                date_col = c
                break
        
        if date_col and date_col != 'date':
            df = df.rename(columns={date_col: 'date'})
        
        return df
    
    except Exception as e:
        print(f' yfinance 錯誤 ({stock_id}): {e}')
        return None

# ==================== SQLite 法人資料讀取 ====================

def get_inst_from_db(stock_id, start_date, end_date):
    """
    從本地 SQLite 讀取法人數據 (推薦方式)
    比每次爬 TWSE 快
    """
    conn = sqlite3.connect(DB_PATH)
    
    query = '''
        SELECT date, foreign_net, trust_net
        FROM MarketData
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date
    '''
    
    df = pd.read_sql_query(query, conn, params=(stock_id, start_date, end_date))
    conn.close()
    
    if len(df) == 0:
        return None
    
    # 計算連續買超天數
    df = df.sort_values('date')
    
    f_consec_list = []
    t_consec_list = []
    
    f_count = 0
    t_count = 0
    
    for _, row in df.iterrows():
        if row['foreign_net'] > 0:
            f_count += 1
        else:
            f_count = 0
        
        if row['trust_net'] > 0:
            t_count += 1
        else:
            t_count = 0
        
        f_consec_list.append(f_count)
        t_consec_list.append(t_count)
    
    df['f_consec'] = f_consec_list
    df['t_consec'] = t_consec_list
    
    return df

# ==================== Nana 數據整合 ====================

def get_nana_data_hybrid(stock_id, start_date, end_date):
    """
    混合抓取 Nana v1.0 所需資料
    1. yfinance 股價
    2. SQLite 法人數據 (本地)
    3. 自動對齊
    """
    print(f'\n 抓取 Nana 資料: {stock_id}')
    print(f' 區間: {start_date} ~ {end_date}')
    
    # 1. 股價
    df_price = get_stock_price_yfinance(stock_id, start_date, end_date)
    
    if df_price is None:
        print(f'  無股價資料')
        return None
    
    print(f'  股價: {len(df_price)} 筆')
    
    # 2. 法人數據
    df_inst = get_inst_from_db(stock_id, start_date, end_date)
    
    if df_inst is None:
        print(f'  無法人資料')
        return None
    
    print(f'  法人: {len(df_inst)} 筆')
    
    # 3. 對齊日期
    df_price['date'] = pd.to_datetime(df_price['date']).dt.strftime('%Y-%m-%d')
    df_inst['date'] = pd.to_datetime(df_inst['date']).dt.strftime('%Y-%m-%d')
    
    # Merge
    df = pd.merge(df_price, df_inst, on='date', how='inner')
    
    if len(df) == 0:
        print(f'  對齊失敗')
        return None
    
    print(f'  對齊後: {len(df)} 筆')
    
    # 4. 技術指標計算
    df = calculate_indicators(df)
    
    return df

def calculate_indicators(df):
    """計算 Nana 所需技術指標"""
    
    # 排序
    df = df.sort_values('date')
    
    # 收盤價
    close = df['close'].values
    
    # MA20, MA60
    df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['ma60'] = df['close'].rolling(window=60, min_periods=1).mean()
    
    # RSI
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = pd.Series(gain).rolling(window=14, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=14, min_periods=1).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + rs))).fillna(50)
    
    # Bias
    df['bias'] = (df['close'] - df['ma20']) / df['ma20'] * 100
    
    # ATR (14日)
    high = df['high'].values
    low = df['low'].values
    
    trs = []
    for i in range(len(df)):
        if i == 0:
            tr = high[i] - low[i]
        else:
            tr = max(high[i] - low[i], 
                    abs(high[i] - close[i-1]),
                    abs(low[i] - close[i-1]))
        trs.append(tr)
    
    df['atr'] = pd.Series(trs).rolling(window=14, min_periods=1).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    return df

# ==================== Nana 評分計算 ====================

def calculate_nana_score(row):
    """計算 Nana 評分 (0-100)"""
    score = 0
    
    # --- 法人評分 (70分) ---
    f_consec = row.get('f_consec', 0)
    t_consec = row.get('t_consec', 0)
    
    # 外資連買天數
    if f_consec == 1:
        score += 10
    elif f_consec == 2:
        score += 15
    elif f_consec == 3:
        score += 40
    elif 4 <= f_consec <= 5:
        score += 50
    elif 6 <= f_consec <= 10:
        score += 60
    elif f_consec > 10:
        score += 20
    
    # 投信合力
    if t_consec >= 3:
        score += 10
    
    # --- 技術評分 (30分) ---
    rsi = row.get('rsi', 50)
    bias = row.get('bias', 0)
    ma20 = row.get('ma20', 0)
    ma60 = row.get('ma60', 0)
    
    # RSI
    if 50 <= rsi <= 70:
        score += 15
    elif 30 <= rsi < 50:
        score += 10
    else:
        score += 5
    
    # Bias
    if -2 <= bias <= 3:
        score += 15
    elif 3 < bias <= 6:
        score += 10
    elif bias > 10:
        score += 0
    else:
        score += 5
    
    # MA 多頭
    if ma20 > ma60:
        score += 0  # 已在上面或下面
    
    return score

def apply_nana_signals(df):
    """對 DataFrame 套用 Nana 訊號"""
    df = df.copy()
    
    # 計算評分
    df['score'] = df.apply(calculate_nana_score, axis=1)
    
    # 進場條件
    df['entry_ok'] = (
        (df['rsi'] >= 40) & (df['rsi'] <= 70) &
        (df['ma20'] > df['ma60']) &
        (df['atr_pct'] >= 0.3) &
        ((df['f_consec'] > 0) | (df['t_consec'] > 0)) &
        (df['score'] >= 80)
    )
    
    # 出場條件
    df['exit_ok'] = (
        (df['score'] < 40) |
        (df['close'] < df['ma20'])
    )
    
    return df

# ==================== 主程式 ====================

def main():
    print('='*60)
    print(' Nana v1.0 Hybrid Data Fetcher')
    print(' yfinance + TWSE + SQLite')
    print('='*60)
    
    # 測試抓取 2330
    df = get_nana_data_hybrid('2330', '2026-01-01', '2026-04-23')
    
    if df is not None:
        # 套用訊號
        df = apply_nana_signals(df)
        
        print()
        print(' 資料概覽:')
        print(df[['date', 'close', 'rsi', 'bias', 'f_consec', 't_consec', 'score', 'entry_ok']].tail(10))
        
        # 計算勝率
        if 'entry_ok' in df.columns:
            signals = df[df['entry_ok']]
            print()
            print(f' 進場訊號: {len(signals)} 次')
    
    # 儲存結果
    if df is not None:
        df.to_csv('Tina_Quant_System/teams/nana/nana_data_sample.csv', index=False)
        print()
        print(' 已儲存: nana_data_sample.csv')

if __name__ == '__main__':
    main()