# -*- coding: utf-8 -*-
"""
Tina 每日市場快報 — 整合所有本地資料庫
=====================================
一次性輸出：
  1. 今日/昨日漲跌停個股
  2. 社群情緒（StockTwits + Reddit + Tavily）
  3. 大盤技術面（RSI、MACD）
  4. 市場廣度（TWSE）
  5. 法人籌碼（FinMind）
"""

import os
import sqlite3
import sys
from datetime import datetime, date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
YFIN_DB = WORKSPACE / "data" / "yfinance.db"
FIN_DB = WORKSPACE / "data" / "finmind.db"
LU_DB = WORKSPACE / "data" / "limitup.db"
ST_DB = WORKSPACE / "data" / "stocktwits_sentiment.db"
RT_DB = WORKSPACE / "data" / "reddit_sentiment.db"
SOC_DB = WORKSPACE / "data" / "social_sentiment.db"


def query_db(db_path, sql, params=()):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        rows = c.execute(sql, params).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def get_last_trading_day():
    """取得最近實際交易日"""
    rows = query_db(YFIN_DB,
        "SELECT date FROM daily_ohlcv ORDER BY date DESC LIMIT 1")
    return rows[0][0] if rows else ''


def market_brief():
    print('=' * 65)
    print('  Tina 每日市場快報')
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} (Asia/Taipei)")
    print('=' * 65)

    last_day = get_last_trading_day()
    print(f'\n📅 最近交易日: {last_day}')
    print()

    # ===== 1. 漲跌停板 =====
    print('─' * 65)
    print('📊 漲跌停板（前日）')
    rows = query_db(LU_DB,
        "SELECT symbol, close, change_pct, volume, type FROM limitup ORDER BY type, change_pct DESC")
    if rows:
        limitup = [r for r in rows if r[4] == 'LIMIT_UP']
        limitdown = [r for r in rows if r[4] == 'LIMIT_DOWN']
        if limitup:
            print('  🔴 漲停:')
            for sym, close, chg, vol, _ in limitup:
                print(f"    {sym}  ${close:.2f}  {chg*100:+.2f}%  Vol={vol:,.0f}")
        if limitdown:
            print('  🔵 跌停:')
            for sym, close, chg, vol, _ in limitdown:
                print(f"    {sym}  ${close:.2f}  {chg*100:+.2f}%  Vol={vol:,.0f}")
    else:
        print('  (無資料)')

    # ===== 2. 社群情緒 Top =====
    print()
    print('💬 社群情緒（StockTwits 多空比）')
    rows = query_db(ST_DB,
        "SELECT ticker, msg_count, bullish_count, bearish_count, sentiment_avg "
        "FROM ticker_stats ORDER BY msg_count DESC LIMIT 8")
    if rows:
        print(f"  {'Ticker':<10} {'Msgs':>5} {'Bull':>5} {'Bear':>5} {'Sent':>8}")
        print('  ' + '-' * 42)
        for ticker, msgs, bull, bear, sent in rows:
            net = bull - bear
            bar = '+' * min(net, 8) if net > 0 else ('-' * min(-net, 8) if net < 0 else '')
            print(f"  {ticker:<10} {msgs:>5} {bull:>5} {bear:>5} {sent:>7.1f} {bar}")
    else:
        print('  (無資料)')

    # ===== 3. Reddit 熱門 =====
    print()
    print('🗳️ Reddit 熱門（總分數）')
    rows = query_db(RT_DB,
        "SELECT ticker, post_count, total_score, sentiment_avg "
        "FROM tickers ORDER BY total_score DESC LIMIT 5")
    if rows:
        for ticker, posts, score, sent in rows:
            print(f"  ${ticker:<8} {score:>6} pts  {posts:>3} posts  sentiment={sent:.1f}")
    else:
        print('  (無資料)')

    # ===== 4. 大盤技術面 =====
    print()
    print('📉 大盤技術面（主要指標）')
    indices = ['^TWII', '^SPX', '^NDX']
    print(f"  {'Index':<10} {'Close':>10} {'RSI14':>7} {'MACD':>10} {'Trend':>8}")
    print('  ' + '-' * 52)
    for idx in indices:
        rows = query_db(YFIN_DB,
            "SELECT close, rsi_14, macd_hist FROM daily_ohlcv "
            "WHERE symbol=? ORDER BY date DESC LIMIT 1", (idx,))
        if rows:
            close, rsi, macd = rows[0]
            trend = '🟢 多頭' if macd and macd > 0 else '🔴 空頭'
            print(f"  {idx:<10} ${close:>9.2f} {rsi if rsi else 'N/A':>7} "
                  f"{(str(round(macd, 2)) if macd else 'N/A'):>10} {trend}")
        else:
            print(f"  {idx:<10} (無資料)")

    # ===== 5. 法人動態（FinMind）=====
    print()
    print('🏛️ 三大法人動態（近5日）')
    stocks = ['2330', '2382', '2317', '2454', '3665']
    print(f"  {'Stock':<10} {'Date':<12} {'BuyVol':>10} {'SellVol':>10} {'Net':>10}")
    print('  ' + '-' * 52)
    for stk in stocks:
        rows = query_db(FIN_DB,
            "SELECT date, buy_volume, sell_volume, net_volume "
            "FROM institutional WHERE stock_id=? ORDER BY date DESC LIMIT 1", (stk,))
        if rows:
            dt, buy, sell, net = rows[0]
            net_str = f"+{net:,}" if net > 0 else f"{net:,}"
            print(f"  {stk:<10} {dt:<12} {buy:>10,} {sell:>10,} {net_str:>10}")
        else:
            print(f"  {stk:<10} (無資料)")

    # ===== 6. 槓桿 ETF 狀態 =====
    print()
    print('⚡ 槓桿/反向 ETF 狀態')
    etfs = [('SOXL', '3x 半導體多'), ('SOXS', '3x 半導體空'), ('TQQQ', '3x Nasdaq多'),
            ('UPRO', '3x S&P500多'), ('SPXL', '3x S&P500多')]
    print(f"  {'ETF':<10} {'Price':>9} {'RSI':>7} {'1D Change':>10} {'Status':<12}")
    print('  ' + '-' * 55)
    for sym, name in etfs:
        rows = query_db(YFIN_DB,
            "SELECT close, rsi_14, change_pct FROM daily_ohlcv "
            "WHERE symbol=? ORDER BY date DESC LIMIT 1", (sym,))
        if rows:
            close, rsi, chg = rows[0]
            status = '🔥 過熱 RSI>70' if rsi and rsi > 70 else ('💤 超賣 RSI<30' if rsi and rsi < 30 else '⚖️ 正常')
            print(f"  {sym:<10} ${close:>8.2f} {rsi if rsi else 0:>6.1f} {chg*100 if chg else 0:>+9.2f}% {status}")
        else:
            print(f"  {sym:<10} (無資料)")

    print()
    print('─' * 65)
    print('[OK] 每日快報完成')


if __name__ == '__main__':
    market_brief()
