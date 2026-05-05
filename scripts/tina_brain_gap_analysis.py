# -*- coding: utf-8 -*-
"""
Tina Brain 能力覆蓋缺口分析
==========================
分析本地資料庫，找出尚未覆蓋的區域
並提出改進建議
"""
import sqlite3, requests, pandas as pd, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

def get_coverage():
    """分析各 DB 覆蓋範圍"""
    results = {}

    # yfinance.db
    conn = sqlite3.connect(str(WORKSPACE / 'data/yfinance.db'))
    c = conn.cursor()
    c.execute('SELECT symbol, COUNT(*) as cnt FROM daily_ohlcv GROUP BY symbol ORDER BY cnt DESC')
    yf_symbols = [r[0] for r in c.fetchall()]
    c.execute('SELECT COUNT(*), COUNT(DISTINCT symbol) FROM daily_ohlcv')
    yf_rows, yf_syms = c.fetchone()
    conn.close()
    results['yfinance'] = {'rows': yf_rows, 'symbols': yf_syms, 'list': yf_symbols}

    # etf.db
    conn = sqlite3.connect(str(WORKSPACE / 'data/etf.db'))
    c = conn.cursor()
    c.execute('SELECT symbol FROM etf_info')
    etf_list = [r[0] for r in c.fetchall()]
    c.execute('SELECT COUNT(*), COUNT(DISTINCT symbol) FROM etf_daily')
    etf_rows, etf_syms = c.fetchone()
    conn.close()
    results['etf'] = {'rows': etf_rows, 'symbols': etf_syms, 'list': etf_list}

    # finmind
    conn = sqlite3.connect(str(WORKSPACE / 'data/finmind.db'))
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM daily_price')
    fm_rows = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM institutional')
    fi_rows = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM futures_daily')
    ff_rows = c.fetchone()[0]
    conn.close()
    results['finmind'] = {'price': fm_rows, 'inst': fi_rows, 'futures': ff_rows}

    # sentiment DBs
    for db_name in ['stocktwits_sentiment', 'reddit_sentiment', 'social_sentiment']:
        try:
            conn = sqlite3.connect(str(WORKSPACE / f'data/{db_name}.db'))
            c = conn.cursor()
            c.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = [r[0] for r in c.fetchall()]
            total = 0
            for t in tables:
                try:
                    c.execute(f'SELECT COUNT(*) FROM {t}')
                    total += c.fetchone()[0]
                except: pass
            results[db_name] = {'total': total}
            conn.close()
        except:
            results[db_name] = {'total': 0}

    return results


def find_gaps(coverage):
    gaps = []

    # Gap 1: 只有美股，沒有港股
    hk_symbols = [s for s in coverage['yfinance']['list'] if any(x in s for x in ['HK.', '9988', '0700', '0005'])]
    if len(hk_symbols) == 0:
        gaps.append(('港股覆蓋', '目前只涵蓋台股/美股，沒有港股（騰訊/阿裡/美團等）'))

    # Gap 2: 沒有期權數據
    gaps.append(('期權數據', '沒有 options/期權 chain 數據'))

    # Gap 3: 沒有個股基本面
    gaps.append(('基本面數據', '沒有營收/財報/殖利率/PER 等基本面'))

    # Gap 4: 沒有外匯數據
    forex_syms = [s for s in coverage['yfinance']['list'] if any(x in s for x in ['USD', 'EUR', 'JPY', 'CNY'])]
    if len(forex_syms) == 0:
        gaps.append(('外匯數據', '沒有 USD/TWD, EUR/USD 等外匯報價'))

    # Gap 5: 沒有虛擬貨幣
    crypto_syms = [s for s in coverage['yfinance']['list'] if any(x in s for x in ['BTC', 'ETH', 'COIN'])]
    if len(crypto_syms) == 0:
        gaps.append(('加密貨幣', '沒有 BTC/ETH 等加密貨幣'))

    # Gap 6: 没有短天期國債殖利率
    tw_bond_syms = [s for s in coverage['yfinance']['list'] if any(x in s for x in ['US02', 'US05', 'US10'])]
    if len(tw_bond_syms) == 0:
        gaps.append(('利率/債市', '沒有短期國債殖利率（2Y/5Y/10Y）'))

    # Gap 7: 只有 TW 和 US，沒有歐股/日股
    regions = {'TW': 0, 'US': 0, 'OTHER': 0}
    for sym in coverage['yfinance']['list']:
        if sym.endswith('.TW') or sym in ['^TWII', '^TAIIR']:
            regions['TW'] += 1
        elif sym.startswith('^') or sym in ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI']:
            regions['US'] += 1
        else:
            regions['OTHER'] += 1
    if regions['OTHER'] < 5:
        gaps.append(('全球市場', f'TW: {regions["TW"]}檔 / US: {regions["US"]}檔 / OTHER: {regions["OTHER"]}檔（偏少）'))

    return gaps


def cross_reference_analysis(coverage):
    """交叉比對分析"""
    issues = []

    # RSI bias 問題（已知問題）
    issues.append(('RSI 偏差', 'yfinance RSI vs FinMind RSI 差 3-15 點，需修正'))

    # 資料新舊問題
    conn = sqlite3.connect(str(WORKSPACE / 'data/yfinance.db'))
    c = conn.cursor()
    c.execute('SELECT MAX(date) FROM daily_ohlcv WHERE symbol=?', ('2330.TW',))
    latest = c.fetchone()[0]
    conn.close()
    issues.append(('數據時效', f'yfinance.db 最新: {latest}'))

    conn = sqlite3.connect(str(WORKSPACE / 'data/etf.db'))
    c = conn.cursor()
    c.execute('SELECT MAX(date) FROM etf_daily WHERE symbol=?', ('0050.TW',))
    etf_latest = c.fetchone()[0]
    conn.close()
    issues.append(('ETF時效', f'etf.db 最新: {etf_latest}'))

    return issues


def main():
    print('='*60)
    print('  Tina Brain 能力覆蓋缺口分析')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    print()
    print('[1/4] 分析本地資料庫覆蓋...')
    cov = get_coverage()

    print()
    print('[2/4] 找出覆蓋缺口...')
    gaps = find_gaps(cov)

    print()
    print('[3/4] 交叉比對已有數據...')
    issues = cross_reference_analysis(cov)

    print()
    print('='*60)
    print('  分析結果')
    print('='*60)
    print()

    print('【覆蓋現況】')
    print('  yfinance.db:  ', cov['yfinance']['rows'], 'rows /', cov['yfinance']['symbols'], 'symbols')
    print('  etf.db:       ', cov['etf']['rows'], 'rows /', cov['etf']['symbols'], 'symbols')
    print('  finmind.db:   ', cov['finmind']['price'], '價格 /', cov['finmind']['inst'], '法人 /', cov['finmind']['futures'], '期貨')
    print('  StockTwits:   ', cov.get('stocktwits_sentiment',{}).get('total',0), 'records')
    print('  Reddit:       ', cov.get('reddit_sentiment',{}).get('total',0), 'records')
    print('  Social:       ', cov.get('social_sentiment',{}).get('total',0), 'records')
    print()

    print('【覆蓋缺口】')
    for name, desc in gaps:
        print('  ⚠️  ' + name + ': ' + desc)
    print()

    print('【數據品質問題】')
    for name, desc in issues:
        print('  🔧  ' + name + ': ' + desc)
    print()

    print('【優先建設】')
    print('  1. 港股覆蓋（騰訊/阿裡/美團/小米/比亞迪）')
    print('  2. 基本面數據（營收/殖利率/PER）')
    print('  3. 外匯/利率數據（USD/TWD, 2Y/10Y國債殖利率）')
    print('  4. RSI 偏差修正（本地DB vs yfinance實時）')
    print('  5. ETF 殖利率排行（Yahoo Finance）')
    print()

    print('='*60)


if __name__ == '__main__':
    main()