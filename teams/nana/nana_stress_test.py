# -*- coding: utf-8 -*-
"""
Nana 系統壓力測試
=================
測試目標:
1. 找出失敗模式
2. 找出數據缺口
3. 找出評分盲點
4. 自動優化
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 測試1: Nana 掃描結果分析 ====================

def test_nana_scan_results():
    """分析 Nana 掃描結果的問題"""
    print('='*60)
    print(' 測試1: Nana 掃描結果分析')
    print('='*60)
    print()
    
    try:
        df = pd.read_json('Tina_Quant_System/teams/nana/scan_result.json')
        
        print(f'總掃描: {len(df)} 檔')
        print()
        
        # 訊號分佈
        print('訊號分佈:')
        for sig, cnt in df['訊號'].value_counts().items():
            print(f'  {sig}: {cnt} ({cnt/len(df)*100:.1f}%)')
        print()
        
        # 分數統計
        print('總分統計:')
        print(f'  平均: {df["總分"].mean():.1f}')
        print(f'  中位數: {df["總分"].median():.1f}')
        print(f'  標準差: {df["總分"].std():.1f}')
        print(f'  最高: {df["總分"].max()}')
        print(f'  最低: {df["總分"].min()}')
        print()
        
        # RSI 分佈
        print('RSI 分佈:')
        rsi_bins = [(0, 40), (40, 60), (60, 70), (70, 85), (85, 100)]
        for low, high in rsi_bins:
            cnt = len(df[(df['RSI'] >= low) & (df['RSI'] < high)])
            print(f'  {low}-{high}: {cnt} 檔 ({cnt/len(df)*100:.1f}%)')
        print()
        
        # 法人分=0的分析
        no_inst = df[df['法人分'] == 0]
        print(f'法人分=0: {len(no_inst)} 檔 ({len(no_inst)/len(df)*100:.1f}%)')
        print()
        
        # 這些股票分數
        if len(no_inst) > 0:
            print('法人分=0 的股票:')
            for _, r in no_inst.iterrows():
                print(f'  {r["代號"]}: 總分={r["總分"]}, RSI={r["RSI"]}, 訊號={r["訊號"]}')
        print()
        
        # 問題: RSI 過高但有進場訊號
        rsi_high = df[(df['RSI'] >= 70) & (df['訊號'].str.contains('買'))]
        if len(rsi_high) > 0:
            print(f'⚠️ RSI>=70 但有買進訊號: {len(rsi_high)} 檔')
            for _, r in rsi_high.iterrows():
                print(f'  {r["代號"]}: RSI={r["RSI"]}, 總分={r["總分"]}')
        print()
        
        return df
        
    except Exception as e:
        print(f'❌ 錯誤: {e}')
        return None

# ==================== 測試2: 資料庫完整性 ====================

def test_database_coverage():
    """測試資料庫覆蓋率"""
    print('='*60)
    print(' 測試2: 資料庫覆蓋率')
    print('='*60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    
    # 取得資料庫中的股票
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM MarketData ORDER BY symbol')
    db_stocks = set([r[0] for r in cur.fetchall()])
    
    # 取得 Nana 股票池
    df = pd.read_json('Tina_Quant_System/teams/nana/scan_result.json')
    scan_stocks = set(df['代號'].values)
    
    # 覆蓋率
    covered = scan_stocks & db_stocks
    uncovered = scan_stocks - db_stocks
    
    print(f'Nana 股票池: {len(scan_stocks)} 檔')
    print(f'資料庫覆蓋: {len(covered)} 檔 ({len(covered)/len(scan_stocks)*100:.1f}%)')
    print(f'未覆蓋: {len(uncovered)} 檔')
    
    if uncovered:
        print(f'未覆蓋股票: {uncovered}')
    print()
    
    # 資料日期範圍
    cur.execute('SELECT MIN(date), MAX(date) FROM MarketData')
    min_date, max_date = cur.fetchone()
    print(f'資料庫日期: {min_date} ~ {max_date}')
    print()
    
    # 各股票資料筆數
    print('資料筆數 (前10):')
    cur.execute('''
        SELECT symbol, COUNT(*) as cnt 
        FROM MarketData 
        GROUP BY symbol 
        ORDER BY cnt DESC 
        LIMIT 10
    ''')
    for symbol, cnt in cur.fetchall():
        print(f'  {symbol}: {cnt} 筆')
    
    conn.close()
    
    return list(uncovered)

# ==================== 測試3: 邊界條件 ====================

def test_edge_cases():
    """邊界條件測試"""
    print()
    print('='*60)
    print(' 測試3: 邊界條件')
    print('='*60)
    print()
    
    # 測試案例
    test_cases = [
        ('2330', '正常'),
        ('0000', '不存在'),
        ('9999', '不存在'),
    ]
    
    for symbol, desc in test_cases:
        try:
            df = yf.download(f'{symbol}.TW', period='5d', auto_adjust=True, progress=False)
            if df is not None and len(df) > 0:
                print(f'  {symbol} ({desc}): ✅ {len(df)} 筆')
            else:
                print(f'  {symbol} ({desc}): ❌ 無資料')
        except Exception as e:
            print(f'  {symbol} ({desc}): ❌ {e}')
    
    print()

# ==================== 測試4: Exit Strategy 壓力測試 ====================

def test_exit_strategy_stress():
    """Exit Strategy 壓力測試"""
    print('='*60)
    print(' 測試4: Exit Strategy 壓力測試')
    print('='*60)
    print()
    
    sys.path.insert(0, 'Tina_Quant_System/core')
    from exit_strategy import ExitStrategy
    
    # 測試情境
    scenarios = [
        # (進場, ATR, 描述)
        (100, 5.0, '高波動'),
        (100, 1.0, '低波動'),
        (100, 0.5, '極低波動'),
        (1000, 50.0, '高價股'),
        (10, 0.2, '低價股'),
    ]
    
    print('進場  ATR   情境    目標價  停損   Trail初始')
    print('-'*55)
    
    for entry, atr, desc in scenarios:
        es = ExitStrategy(entry, atr, target_ratio=0.10, stop_ratio=0.05)
        print(f'${entry:<4} ${atr:<4} {desc:<8} ${es.target_price:<6.0f} ${es.stop_price:<6.0f} ${es.trailing_stop:<6.2f}')
    
    print()
    
    # 極端情境測試
    print('極端情境:')
    es = ExitStrategy(entry=100, atr=0.1, atr_multiplier=3.0, target_ratio=0.20)
    print(f'  ATR極低(0.1) + ATR倍數3x + 目標20%')
    print(f'  Trail初始: ${es.trailing_stop:.2f} (進場後馬上可能被觸發)')
    
    # 測試 ATR 0 的情況
    print()
    print('ATR=0 測試:')
    try:
        es2 = ExitStrategy(entry=100, atr=0, atr_multiplier=2.5)
        print(f'  ❌ 應該報錯但沒報')
    except:
        print(f'  ✅ ATR=0 正確處理')

# ==================== 測試5: Position Sizing 壓力測試 ====================

def test_position_sizing_stress():
    """Position Sizing 壓力測試"""
    print()
    print('='*60)
    print(' 測試5: Position Sizing 壓力測試')
    print('='*60)
    print()
    
    sys.path.insert(0, 'Tina_Quant_System/core')
    from position_sizing import PositionSizer
    
    ps = PositionSizer(
        total_capital=3_000_000,
        max_position_ratio=0.15,
        risk_per_trade=0.02,
        win_rate=0.54,
        avg_win=0.0142,
        avg_loss=-0.01
    )
    
    # 正常情境
    result = ps.calculate_size('2330', entry_price=200, stop_loss=190)
    print(f'正常: {result["shares"]} 股, 金額 ${result["investment"]:,.0f}')
    
    # 停損=進場價
    result2 = ps.calculate_size('2330', entry_price=200, stop_loss=200)
    print(f'停損=進場: {result2["warning"]}')
    
    # 信心度 2x
    result3 = ps.calculate_size('2330', entry_price=200, stop_loss=190, confidence=2.0)
    print(f'信心2x: {result3["shares"]} 股')
    
    # 小資金
    ps_small = PositionSizer(total_capital=100_000, max_position_ratio=0.20)
    result4 = ps_small.calculate_size('2330', entry_price=200, stop_loss=190)
    print(f'小資金(10萬): {result4["shares"]} 股, {result4["warning"] if result4["warning"] else "正常"}')

# ==================== 測試6: Sector Rotation 資料完整性 ====================

def test_sector_rotation():
    """Sector Rotation 測試"""
    print()
    print('='*60)
    print(' 測試6: Sector Rotation 資料完整性')
    print('='*60)
    print()
    
    sys.path.insert(0, 'Tina_Quant_System/core')
    from sector_rotation import SectorRotation
    
    sr = SectorRotation(period=20)
    
    # 只測試 3 個產業
    import yfinance as yf
    
    test_sectors = ['半導體', '金融', '食品']
    
    for sector in test_sectors:
        try:
            stocks = ['2330', '2881', '1216']  # 對應股票
            df = yf.download(f'{stocks[test_sectors.index(sector)]}.TW', 
                           period='30d', auto_adjust=True, progress=False)
            print(f'  {sector}: ✅ {len(df)} 筆')
        except Exception as e:
            print(f'  {sector}: ❌ {e}')

# ==================== 主程式 ====================

def main():
    print()
    print('╔' + '═'*58 + '╗')
    print('║' + ' '*15 + 'Nana 系統壓力測試' + ' '*21 + '║')
    print('╚' + '═'*58 + '╝')
    print()
    
    # 執行所有測試
    df = test_nana_scan_results()
    uncovered = test_database_coverage()
    test_edge_cases()
    test_exit_strategy_stress()
    test_position_sizing_stress()
    test_sector_rotation()
    
    # ==================== 問題總結 ====================
    print()
    print('='*60)
    print(' 🔴 發現的問題')
    print('='*60)
    print()
    
    problems = []
    
    if df is not None:
        # 問題1: 法人分=0 但有進場
        no_inst_buy = df[(df['法人分'] == 0) & (df['訊號'].str.contains('買'))]
        if len(no_inst_buy) > 0:
            problems.append(f'法人分=0 但有進場訊號: {len(no_inst_buy)} 檔')
        
        # 問題2: RSI 過高
        rsi_high_buy = df[(df['RSI'] >= 70) & (df['訊號'].str.contains('買'))]
        if len(rsi_high_buy) > 0:
            problems.append(f'RSI>=70 但有買進訊號: {len(rsi_high_buy)} 檔')
        
        # 問題3: 分數過低但有訊號
        low_score_buy = df[(df['總分'] < 40) & (df['訊號'].str.contains('買'))]
        if len(low_score_buy) > 0:
            problems.append(f'總分<40 但有買進訊號: {len(low_score_buy)} 檔')
    
    if uncovered:
        problems.append(f'資料庫未覆蓋: {len(uncovered)} 檔')
    
    if problems:
        for i, p in enumerate(problems, 1):
            print(f'  {i}. ⚠️  {p}')
    else:
        print('  ✅ 未發現重大問題')
    
    print()
    print('='*60)
    print(' 💡 優化建議')
    print('='*60)
    print()
    print('  1. 加入法人分門檻: 法人分>0 才能進場')
    print('  2. 加入 RSI 上限: RSI>=75 應排除')
    print('  3. 提高最低分數門檻: 從 40 提高到 50')
    print('  4. 擴充資料庫: 補充未覆蓋股票')
    print()
    print('='*60)

if __name__ == '__main__':
    main()