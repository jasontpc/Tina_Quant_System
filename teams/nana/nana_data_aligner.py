# -*- coding: utf-8 -*-
"""
Nana v1.0 資料格式轉換與自動對齊系統
=====================================

功能:
1. TWSE 法人資料批次抓取 (民國年轉西元)
2. yfinance 股價資料對齊
3. 欄位名稱標準化
4. 空缺值處理
5. 時間戳記一致性

專業建議:
- 批次處理優先於逐日抓取
- 統一使用 fillna(0) 處理法人空缺
- 欄位名稱標準化
- Timestamp 必須一致才能正確 Merge
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import sqlite3
from datetime import datetime, timedelta
from io import StringIO

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 日期轉換工具 ====================

def roc_to_ce(roc_date_str):
    """
    將 '115/04/23' 轉換為 '2026-04-23'
    民國年 = 西元年 - 1911
    """
    try:
        parts = roc_date_str.strip().split('/')
        year = int(parts[0]) + 1911
        month = parts[1].zfill(2)
        day = parts[2].zfill(2)
        return f"{year}-{month}-{day}"
    except:
        return None

def date_to_roc(date_str):
    """
    將 '2026-04-23' 轉換為 '115/04/23'
    """
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        roc_year = dt.year - 1911
        return f"{roc_year}/{dt.month:02d}/{dt.day:02d}"
    except:
        return None

# ==================== TWSE 法人資料抓取 ====================

def fetch_twse_daily_institutional(date_str):
    """
    抓取 TWSE 當日三大法人買賣超 (全市場)
    
    參數:
        date_str: '20260423' (民國格式無斜線)
    
    返回:
        DataFrame with columns: Code, Foreign_Net, Trust_Net
    """
    url = f"https://www.twse.com.tw/fund/T86W"
    params = {
        'response': 'csv',
        'date': date_str,
        'selectType': 'ALL'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/csv',
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200 or len(response.text) < 100:
            return None
        
        # 解析 CSV (跳過首行說明文字)
        lines = response.text.split('\n')
        
        # 找到欄位標題行 (通常在第2行)
        header_idx = 0
        for i, line in enumerate(lines):
            if '證券代號' in line:
                header_idx = i
                break
        
        # 讀取 CSV
        from io import StringIO
        csv_text = '\n'.join(lines[header_idx:])
        df = pd.read_csv(StringIO(csv_text))
        
        # 清理空白欄位
        df = df.dropna(axis=1, how='all')
        
        # 找到目標欄位
        # 常見欄位: '證券代號', '外陸資買進股數(不含外資自營商)', '外陸資賣出股數(不含外資自營商)', ...
        # 我們需要: 外資淨買, 投信淨買
        
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if '證券代號' in col:
                col_map['code'] = col
            elif ('外陸資' in col or '外资' in col) and ('買進' in col or '买进' in col) and '自營' not in col:
                col_map['foreign_buy'] = col
            elif ('外陸資' in col or '外资' in col) and ('賣出' in col or '卖出' in col) and '自營' not in col:
                col_map['foreign_sell'] = col
            elif '投信' in col and '買進' in col:
                col_map['trust_buy'] = col
            elif '投信' in col and '賣出' in col:
                col_map['trust_sell'] = col
        
        # 轉換欄位
        if 'code' not in col_map:
            return None
        
        result = df[['證券代號']].copy()
        result.columns = ['Code']
        
        if 'foreign_buy' in col_map and 'foreign_sell' in col_map:
            result['Foreign_Buy'] = pd.to_numeric(df[col_map['foreign_buy']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            result['Foreign_Sell'] = pd.to_numeric(df[col_map['foreign_sell']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            result['Foreign_Net'] = result['Foreign_Buy'] - result['Foreign_Sell']
        
        if 'trust_buy' in col_map and 'trust_sell' in col_map:
            result['Trust_Buy'] = pd.to_numeric(df[col_map['trust_buy']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            result['Trust_Sell'] = pd.to_numeric(df[col_map['trust_sell']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            result['Trust_Net'] = result['Trust_Buy'] - result['Trust_Sell']
        
        # 設定日期
        ce_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        result['Date'] = ce_date
        
        return result
    
    except Exception as e:
        print(f' TWSE fetch error: {e}')
        return None

def batch_fetch_and_save_institutional(start_date, end_date, db_path=DB_PATH):
    """
    批次抓取法人資料並存入 SQLite
    
    這是推薦的流程:
    1. 每天只 call 一次 TWSE API (全市場)
    2. 存入本地資料庫
    3. 回測時直接從資料庫讀取
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    current = start_dt
    total_days = (end_dt - start_dt).days + 1
    
    print(f' 批次抓取法人資料: {start_date} ~ {end_date} ({total_days} 天)')
    
    saved_count = 0
    error_count = 0
    
    while current <= end_dt:
        date_str = current.strftime('%Y%m%d')
        
        # 檢查是否已存在
        cur.execute('SELECT COUNT(*) FROM MarketData WHERE date >= ? AND date <= ?', 
                   (current.strftime('%Y-%m-%d'), current.strftime('%Y-%m-%d')))
        exists = cur.fetchone()[0] > 0
        
        if not exists:
            df = fetch_twse_daily_institutional(date_str)
            
            if df is not None and len(df) > 0:
                # 存入資料庫
                for _, row in df.iterrows():
                    try:
                        cur.execute('''
                            INSERT OR REPLACE INTO MarketData (date, symbol, foreign_net, trust_net)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            row['Date'],
                            str(row['Code']).strip(),
                            row.get('Foreign_Net', 0),
                            row.get('Trust_Net', 0)
                        ))
                    except:
                        pass
                
                saved_count += 1
                print(f'  {current.strftime("%Y-%m-%d")}: {len(df)} 筆')
            else:
                error_count += 1
        
        time.sleep(3)  # 防爬蟲
        current += timedelta(days=1)
    
    conn.commit()
    conn.close()
    
    print(f'\n 完成: 成功 {saved_count} 天, 失敗 {error_count} 天')
    return saved_count, error_count

# ==================== yfinance 股價抓取 ====================

def fetch_price_yfinance(stock_id, start_date, end_date):
    """
    抓取 yfinance 股價資料
    自動處理還原股價 (Adjusted Close)
    """
    ticker = f"{stock_id}.TW"
    
    try:
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
        
        if df is None or len(df) == 0:
            return None
        
        # 處理 MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        df = df.reset_index()
        
        # 統一欄位名稱
        df.columns = [str(c).lower() for c in df.columns]
        
        # 確保有 date 欄位
        for c in df.columns:
            if 'date' in c.lower():
                if c != 'date':
                    df = df.rename(columns={c: 'date'})
                break
        
        # 移除時分秒
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        return df
    
    except Exception as e:
        return None

# ==================== 資料對齊 (Merge) ====================

def align_stock_data(stock_id, start_date, end_date, use_db=True):
    """
    對齊股價與法人資料
    
    對齊策略:
    - 若 use_db=True: 從 SQLite 讀取法人資料 (推薦)
    - 若 use_db=False: 嘗試 TWSE API 即時抓取
    
    返回:
        DataFrame with columns: Date, Open, High, Low, Close, Volume, Foreign_Net, Trust_Net
    """
    # 1. 抓取股價
    df_price = fetch_price_yfinance(stock_id, start_date, end_date)
    
    if df_price is None or len(df_price) == 0:
        return None
    
    # 2. 法人資料
    if use_db:
        # 從 SQLite 讀取
        conn = sqlite3.connect(DB_PATH)
        query = '''
            SELECT date, foreign_net, trust_net
            FROM MarketData
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        '''
        df_inst = pd.read_sql_query(query, conn, params=(stock_id, start_date, end_date))
        conn.close()
        
        if len(df_inst) == 0:
            print(f' 無法人資料: {stock_id}')
            # 只返回股價資料
            df_price = df_price.rename(columns={'foreign_net': 'Foreign_Net', 'trust_net': 'Trust_Net'})
            df_price['Foreign_Net'] = 0
            df_price['Trust_Net'] = 0
            return df_price
        
        df_inst.columns = ['Date', 'Foreign_Net', 'Trust_Net']
    else:
        # 即時抓取 (不推薦，容易被封)
        df_inst = None
    
    # 3. Merge
    if df_inst is not None and len(df_inst) > 0:
        df_price['date'] = pd.to_datetime(df_price['date']).dt.strftime('%Y-%m-%d')
        df_inst['Date'] = pd.to_datetime(df_inst['Date']).dt.strftime('%Y-%m-%d')
        
        df = pd.merge(df_price, df_inst, left_on='date', right_on='Date', how='left')
        
        # 移除重複欄位
        if 'Date' in df.columns and 'date' in df.columns:
            df = df.drop(columns=['Date'])
    else:
        df = df_price
        df['Foreign_Net'] = 0
        df['Trust_Net'] = 0
    
    # 4. 填充空缺值 (法人無資料 = 0)
    df['Foreign_Net'] = df['Foreign_Net'].fillna(0)
    df['Trust_Net'] = df['Trust_Net'].fillna(0)
    
    # 5. 計算連續買超天數
    df = df.sort_values('date')
    
    f_consec_list = []
    t_consec_list = []
    
    f_count = 0
    t_count = 0
    
    for _, row in df.iterrows():
        if row['Foreign_Net'] > 0:
            f_count += 1
        else:
            f_count = 0
        
        if row['Trust_Net'] > 0:
            t_count += 1
        else:
            t_count = 0
        
        f_consec_list.append(f_count)
        t_consec_list.append(t_count)
    
    df['F_Consec'] = f_consec_list
    df['T_Consec'] = t_consec_list
    
    return df

# ==================== 欄位標準化 ====================

def standardize_columns(df):
    """
    標準化欄位名稱
    適用於 TWSE 或其他來源
    """
    rename_map = {
        'date': 'Date',
        'close': 'Close',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'volume': 'Volume',
        'foreign_net': 'Foreign_Net',
        'trust_net': 'Trust_Net',
        'f_consec': 'F_Consec',
        't_consec': 'T_Consec',
        'rsi': 'RSI',
        'ma20': 'MA20',
        'ma60': 'MA60',
        'bias': 'Bias',
        'atr': 'ATR',
        'score': 'Score'
    }
    
    df = df.rename(columns=rename_map)
    
    return df

# ==================== 主程式測試 ====================

def main():
    print('='*60)
    print(' Nana v1.0 資料格式轉換與自動對齊')
    print('='*60)
    
    # 測試單一股票對齊
    stock_id = '2330'
    start = '2026-01-01'
    end = '2026-04-23'
    
    print(f'\n 對齊資料: {stock_id} ({start} ~ {end})')
    
    df = align_stock_data(stock_id, start, end, use_db=True)
    
    if df is not None:
        df = standardize_columns(df)
        
        print(f'\n 對齊後: {len(df)} 筆')
        print()
        print(' 欄位:', list(df.columns))
        print()
        print(' 最後5筆:')
        print(df[['Date', 'Close', 'Foreign_Net', 'F_Consec', 'T_Consec']].tail())
        
        # 儲存
        df.to_csv('Tina_Quant_System/teams/nana/aligned_data_sample.csv', index=False)
        print()
        print(' 已儲存: aligned_data_sample.csv')
    
    else:
        print(' 無法對齊資料')

if __name__ == '__main__':
    main()