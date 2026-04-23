# -*- coding: utf-8 -*-
"""
Nana v1.0 台股百大自動化掃描腳本
==================================

功能:
1. 批次掃描台股前100大
2. 量化評分 (NanaScorer)
3. 產出今日 Top 10 報告
4. 進度條 + 錯誤處理
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import time
from datetime import datetime
import json

# 載入 NanaScorer
from nana_scorer import NanaScorer
from nana_data_aligner import align_stock_data

# ==================== 台股百大名單 ====================

TOP100_STOCKS = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2492','2610','2880','2881','2882','2883','2884','2885',
    '2886','2887','2891','2892','3008','3033','3044','3189','3231','3443',
    '3481','3665','3717','4938','4958','6415','6505','6669','6770','8016',
    '8046','8105','8261','8341','8464','8926','8996','9945','2385','2603',
    '2890','2888','5880','5871','1234','5871','2303','2327','2344','2515',
    '2527','2707','2834','2855','2912','3029','3045','3294','3305','3380',
    '3416','3533','3557','3593','3596','3673','3686','3702','3711','4001'
]

def nana_market_scanner(stock_list, start_date, end_date, delay=0.5):
    """
    掃描清單中的股票，並回傳評分結果總表
    
    參數:
        stock_list: 股票代碼列表
        start_date: 資料起始日
        end_date: 資料結束日
        delay: 每次抓取後的延遲秒數 (防爬蟲)
    
    返回:
        DataFrame with columns: 代號, 名稱, 今日價格, 總分, 信號, 法人分, 技術分, RSI, Bias
    """
    results = []
    errors = []
    
    print(f'🚀 Nana v1.0 開始掃描市場，目標總數：{len(stock_list)}')
    print()
    
    for i, stock_id in enumerate(stock_list, 1):
        try:
            # 抓取並對齊資料
            df = align_stock_data(stock_id, start_date, end_date, use_db=True)
            
            if df is None or len(df) == 0:
                errors.append((stock_id, '無資料'))
                continue
            
            # 評分
            scorer = NanaScorer(df)
            scored_df = scorer.calculate_scores()
            
            # 取得最新一筆
            latest = scored_df.iloc[-1]
            
            # 計算技術分
            tech_score = latest.get('RSI_Score', 0) + latest.get('Bias_Score', 0)
            
            res = {
                '代號': stock_id,
                '日期': latest.get('Date', latest.get('date', end_date)),
                '今日價格': latest.get('Close', latest.get('close', 0)),
                '總分': int(latest['Total_Score']),
                '信號': latest['Signal'],
                '法人分': int(latest.get('Final_Inst_Score', 0)),
                '技術分': int(tech_score),
                'RSI': round(latest.get('RSI', 0), 1),
                'Bias': round(latest.get('Bias', 0), 1),
                'F_Consec': int(latest.get('F_Consec', 0)),
                'T_Consec': int(latest.get('T_Consec', 0)),
                'MA20': round(latest.get('MA20', 0), 2),
                'MA60': round(latest.get('MA60', 0), 2)
            }
            
            results.append(res)
            
            # 進度顯示
            if i % 10 == 0 or i == len(stock_list):
                print(f'  已掃描: {i}/{len(stock_list)} ({i/len(stock_list)*100:.0f}%)')
            
            # 防爬蟲延遲
            time.sleep(delay)
        
        except Exception as e:
            errors.append((stock_id, str(e)))
            continue
    
    # 建立結果 DataFrame
    result_df = pd.DataFrame(results)
    
    print()
    print(f'✅ 掃描完成: 成功 {len(results)} 檔, 失敗 {len(errors)} 檔')
    
    if errors:
        print(f'❌ 失敗標的: {[e[0] for e in errors[:5]]}{"..." if len(errors) > 5 else ""}')
    
    return result_df, errors

def generate_top10_report(df, min_score=60):
    """
    產出今日 Top 10 報告
    
    排序邏輯:
    1. 總分由高到低
    2. 若總分相同，參考 RSI (動能較強者優先)
    """
    if df is None or len(df) == 0:
        return None
    
    # 過濾進場訊號 (買進 或 強力買進)
    buy_signals = df[df['信號'].isin(['買進', '⭐️ 強力買進'])]
    
    # 排序: 總分 DESC, RSI DESC
    sorted_df = buy_signals.sort_values(
        by=['總分', 'RSI'], 
        ascending=[False, False]
    ).head(10)
    
    return sorted_df

def print_top10_report(top10_df, title='Nana v1.0 今日波段掃描報告'):
    """格式化輸出 Top 10 報告"""
    print()
    print('='*70)
    print(f'📊 {title} - Top 10')
    print('='*70)
    print()
    
    if top10_df is None or len(top10_df) == 0:
        print(' 今日無符合進場門檻之標的。')
        print('='*70)
        return
    
    # 表格標題
    print('%-6s %-10s %-8s %-7s %-7s %-6s %-6s %-5s %-5s' % (
        '代號', '日期', '價格', '總分', '法人', '技術', 'RSI', 'Bias', '訊號'))
    print('-'*70)
    
    # 資料列
    for _, row in top10_df.iterrows():
        print('%-6s %-10s %-8.0f %-7d %-7d %-6d %-6.1f %-5.1f %-5s' % (
            row['代號'],
            row['日期'],
            row['今日價格'],
            row['總分'],
            row['法人分'],
            row['技術分'],
            row['RSI'],
            row['Bias'],
            row['信號']
        ))
    
    print()
    print('='*70)
    print()
    
    # 額外建議
    if len(top10_df) > 0:
        best = top10_df.iloc[0]
        print(f' 🏆 最佳標的: {best["代號"]} (總分 {best["總分"]})')
        print(f'    價格: {best["今日價格"]:.0f} | RSI: {best["RSI"]:.1f} | Bias: {best["Bias"]:.1f}')
        
        if best['F_Consec'] > 0 or best['T_Consec'] > 0:
            print(f'    法人: 外資{best["F_Consec"]}天 + 投信{best["T_Consec"]}天')

def save_report(df, top10_df, errors):
    """儲存報告到 JSON"""
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': len(df) if df is not None else 0,
        'total_errors': len(errors),
        'top10': top10_df.to_dict('records') if top10_df is not None and len(top10_df) > 0 else [],
        'all_results': df.to_dict('records') if df is not None else [],
        'errors': [{'stock': e[0], 'error': e[1]} for e in errors]
    }
    
    filepath = 'Tina_Quant_System/teams/nana/market_scan_report.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f' 已儲存: {filepath}')

# ==================== 主程式 ====================

def main():
    print('='*70)
    print(' Nana v1.0 台股百大自動化掃描腳本')
    print('='*70)
    print()
    
    # 掃描區間 (最近90天)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f' 掃描區間: {start_date} ~ {end_date}')
    print(f' 目標: {len(TOP100_STOCKS)} 檔股票')
    print()
    
    # 執行掃描
    result_df, errors = nana_market_scanner(
        TOP100_STOCKS, 
        start_date, 
        end_date,
        delay=0.3  # yfinance 可設短一點
    )
    
    # 產出 Top 10
    top10_df = generate_top10_report(result_df, min_score=60)
    
    # 印出報告
    print_top10_report(top10_df)
    
    # 儲存報告
    save_report(result_df, top10_df, errors)
    
    return result_df, top10_df, errors

if __name__ == '__main__':
    main()