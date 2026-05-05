# -*- coding: utf-8 -*-
"""
Tina 百元成長股篩選器 v2
=======================
條件：
  • 價格 < $100
  • 有動能：MACD > 0
  • 有波動：ATR > 1.5% of price
  • RSI 健康：30 < RSI < 70（偏多區間 40-60 最佳）
  • 今日未下跌
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
YFIN_DB = WORKSPACE / "data" / "yfinance.db"

def screen_growth_stocks():
    conn = sqlite3.connect(YFIN_DB)
    c = conn.cursor()

    c.execute('''
        SELECT
            symbol, date, close, rsi_14, macd_hist,
            atr_14, vol_ratio, sma_20, sma_60, change_pct
        FROM daily_ohlcv
        WHERE symbol IN (
            SELECT symbol FROM daily_ohlcv GROUP BY symbol HAVING COUNT(*) >= 60
        )
        AND date = (SELECT MAX(date) FROM daily_ohlcv d2 WHERE d2.symbol = daily_ohlcv.symbol)
        AND close < 100
        AND close > 1
        ORDER BY change_pct DESC
    ''')
    rows = c.fetchall()
    conn.close()

    print('=' * 65)
    print('  Tina 百元成長股篩選')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    print()

    candidates = []
    for row in rows:
        sym, dt, close, rsi, macd, atr, vol_r, sma20, sma60, chg = row
        if not rsi or not close:
            continue
        if rsi < 30 or rsi > 70:
            continue
        if atr and close:
            atr_pct = (atr / close) * 100
            if atr_pct < 1.5:
                continue
        else:
            continue
        has_momentum = (macd and macd > 0) or (rsi and 40 <= rsi <= 60)
        if not has_momentum:
            continue
        candidates.append({
            'symbol': sym, 'date': dt, 'close': float(close),
            'rsi': float(rsi), 'macd': float(macd) if macd else 0,
            'atr_pct': (float(atr)/float(close)*100) if atr and close else 0,
            'vol_ratio': float(vol_r) if vol_r else 1.0,
            'chg': float(chg) if chg else 0,
        })

    if not candidates:
        print('無符合條件的股票（請確認 yfinance.db 已有足夠資料）')
        return

    scored = []
    for c2 in candidates:
        score = 0
        if 40 <= c2['rsi'] <= 50:
            score += 30
        elif 30 <= c2['rsi'] < 40:
            score += 15
        if c2['macd'] > 0:
            score += 20
        if c2['atr_pct'] > 3:
            score += 10
        if c2['vol_ratio'] > 1.5:
            score += 10
        if c2['close'] < 50:
            score += 10
        if c2['chg'] > 0:
            score += 5
        c2['score'] = score
        scored.append(c2)

    scored.sort(key=lambda x: x['score'], reverse=True)

    print(f"符合條件：{len(scored)} 檔")
    print()
    print('%-12s %7s %6s %8s %6s %5s %6s %6s  評語' % ('Symbol', 'Price', 'RSI', 'MACD', 'ATR%', 'VolR', '1D%', 'Score'))
    print('-' * 70)

    for s in scored[:25]:
        if 40 <= s['rsi'] <= 50:
            zone = '🟢 進場區'
        elif s['rsi'] < 60:
            zone = '🔵 偏多'
        else:
            zone = '⚠️ 偏高'
        print('%-12s %7.2f %6.1f %8.2f %5.1f%% %5.1f %+6.2f%% %5d  %s' % (
            s['symbol'], s['close'], s['rsi'],
            s['macd'], s['atr_pct'], s['vol_ratio'],
            s['chg']*100, s['score'], zone
        ))

    print()
    print('篩選邏輯：')
    print('  RSI 30-70（40-50 進場區=30分 | 30-40/50-60=15分）')
    print('  MACD>0=20分 | ATR>3%=10分 | VolR>1.5=10分')
    print('  價格<50=10分 | 今日上漲=5分')


if __name__ == '__main__':
    screen_growth_stocks()
