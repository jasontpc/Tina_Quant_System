# -*- coding: utf-8 -*-
"""
Ray DCA Backtest Tool — 定期定額回測工具（v2）
假設每週定期定額 $1000，持续52週，對比 Buy & Hold
使用 rolling window 方式：從 start_date 開始，每週投入直到 end_date
用法: python dca_backtest.py [ETF代碼] [每週金額] [週數]
例如: python dca_backtest.py 00919 1000 52
"""
import yfinance as yf
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+'
}


def dca_backtest(etf_id, weekly_amount=1000, weeks=52, end_date=None):
    """
    DCA 回測（rolling window 精確版本）
    - 從 end_date 往前滾動，每7天投入一次
    - Buy&Hold: 期初一次投入同等總金額，持有到期末
    """
    sym = etf_id + '.TW'
    name = ETF_NAMES.get(etf_id, etf_id)
    end_dt = pd.Timestamp(end_date).tz_localize(None) if end_date else pd.Timestamp.now().tz_localize(None)
    start_dt = (end_dt - timedelta(weeks=weeks)).tz_localize(None)

    # 抓取足夠歷史數據
    buffer = timedelta(weeks=weeks + 4)
    h = yf.Ticker(sym).history(start=start_dt - buffer, end=end_dt + timedelta(days=1))
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']

    if len(close) < weeks:
        print(f'⚠️ {name} ({etf_id}) 歷史數據不足（需要{weeks}週，只有{len(close)}天）')
        return None

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    # 確保 close index 是 UTC-free naive datetime
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)

    # 嚴格從 start_dt 到 end_dt，每7天一筆
    # 以 start_dt 為基準，每7天取一次
    dca_dates = pd.date_range(start=start_dt, end=end_dt, freq='7D')
    # 確保 dca_dates 也是 naive
    if dca_dates.tz is not None:
        dca_dates = dca_dates.tz_localize(None)

    # 對每個 DCA 日期，找到當天或之前最近的價格
    dca_prices = []
    valid_dates = []
    for d in dca_dates:
        available = close[close.index <= d]
        if len(available) > 0:
            dca_prices.append(available.iloc[-1])
            valid_dates.append(available.index[-1])
        else:
            pass

    dca_prices = pd.Series(dca_prices)
    dca_prices.index = dca_dates[:len(dca_prices)]

    if len(dca_prices) < weeks // 2:
        print(f'⚠️ {name} ({etf_id}) 可用數據不足（需要{weeks}筆，只有{len(dca_prices)}筆）')
        return None

    # ===== DCA 模擬 =====
    dca_total_cost = 0
    dca_total_units = 0
    dca_schedule = []

    for i, (dt, price) in enumerate(dca_prices.items()):
        units = weekly_amount / price
        dca_total_cost += weekly_amount
        dca_total_units += units
        dca_schedule.append({
            'week': i + 1,
            'date': dt.strftime('%Y-%m-%d'),
            'actual_date': valid_dates[i].strftime('%Y-%m-%d'),
            'price': round(price, 2),
            'amount': weekly_amount,
            'units': round(units, 4)
        })

    # ===== Buy & Hold 模擬 =====
    bh_first_price = dca_prices.iloc[0]
    bh_last_price = dca_prices.iloc[-1]
    bh_total_units = dca_total_cost / bh_first_price
    bh_final_value = bh_total_units * bh_last_price

    # ===== DCA 最終市值 =====
    dca_final_value = dca_total_units * bh_last_price
    dca_avg_cost = dca_total_cost / dca_total_units

    # ===== 績效計算 =====
    dca_return_pct = (dca_final_value - dca_total_cost) / dca_total_cost * 100
    bh_return_pct = (bh_final_value - dca_total_cost) / dca_total_cost * 100
    dca_vs_bh = dca_return_pct - bh_return_pct

    # ===== 平均成本 vs 期初價格 =====
    dca_wins_on_cost = dca_avg_cost < bh_first_price

    # ===== 回測區間內的最高/最低價 =====
    period_high = float(dca_prices.max())
    period_low = float(dca_prices.min())
    final_price = float(dca_prices.iloc[-1])
    period_pos = (final_price - period_low) / (period_high - period_low) * 100 if period_high > period_low else 50

    # ===== 輸出 =====
    print()
    print('=' * 65)
    print(f'  Ray DCA 回測報告 — {name} ({etf_id})')
    print('=' * 65)
    print(f'  回測期間: {dca_prices.index[0].strftime("%Y-%m-%d")} ~ {dca_prices.index[-1].strftime("%Y-%m-%d")}')
    print(f'  總投入週數: {len(dca_prices)} 週')
    print(f'  每次投入: ${weekly_amount:,}')
    print(f'  區間價格: ${period_low:.2f} ~ ${period_high:.2f}')
    print(f'  期末位置: {period_pos:.1f}%')
    print()
    print('-' * 65)
    print(f'  【DCA 定期定額】')
    print(f'  總投入成本: ${dca_total_cost:,.0f}')
    print(f'  累計單位數: {dca_total_units:,.4f}')
    print(f'  平均成本均價: ${dca_avg_cost:.2f}')
    print(f'  目前市值: ${dca_final_value:,.0f}')
    print(f'  帳面獲利: ${dca_final_value - dca_total_cost:,.0f}')
    print(f'  報酬率: {dca_return_pct:+.2f}%')
    print()
    print('-' * 65)
    print(f'  【Buy & Hold 一次買入】')
    print(f'  買入價格: ${bh_first_price:.2f} ({dca_prices.index[0].strftime("%Y-%m-%d")})')
    print(f'  持有單位數: {bh_total_units:,.4f}')
    print(f'  期末價格: ${bh_last_price:.2f} ({dca_prices.index[-1].strftime("%Y-%m-%d")})')
    print(f'  目前市值: ${bh_final_value:,.0f}')
    print(f'  報酬率: {bh_return_pct:+.2f}%')
    print()
    print('-' * 65)
    print(f'  【DCA vs Buy & Hold】')
    if dca_vs_bh > 0:
        print(f'  ✓ DCA 勝出: +{dca_vs_bh:.2f}%')
    else:
        print(f'  ✗ Buy&Hold 勝出: {abs(dca_vs_bh):.2f}%')
    print()
    print('  【關鍵洞察】')
    if dca_wins_on_cost:
        print(f'  ✓ DCA 平均成本 ${dca_avg_cost:.2f} < Buy&Hold 進場價 ${bh_first_price:.2f}')
        print(f'    → DCA 有效降低進場成本')
    else:
        print(f'  ✗ DCA 平均成本 ${dca_avg_cost:.2f} > Buy&Hold 進場價 ${bh_first_price:.2f}')
        print(f'    → Buy&Hold 在此區間較優')
    if period_high == bh_last_price:
        print(f'  ⚠️ 期末價格等於區間高點，市場可能已過熱')
    print('=' * 65)

    # 最近5筆 DCA 明細
    print()
    print('  【最近5筆 DCA 紀錄】')
    for row in dca_schedule[-5:]:
        print(f'    第{row["week"]:2d}週 (實際{row["actual_date"]}) 價格=${row["price"]:.2f} 買入${row["amount"]:,} → +{row["units"]:.4f}單位')

    return {
        'etf_id': etf_id,
        'name': name,
        'period_weeks': len(dca_prices),
        'period_start': dca_prices.index[0].strftime('%Y-%m-%d'),
        'period_end': dca_prices.index[-1].strftime('%Y-%m-%d'),
        'dca_total_cost': round(dca_total_cost, 0),
        'dca_total_units': round(dca_total_units, 4),
        'dca_avg_cost': round(dca_avg_cost, 2),
        'dca_final_value': float(round(dca_final_value, 0)),
        'dca_return_pct': float(round(dca_return_pct, 2)),
        'bh_first_price': float(round(bh_first_price, 2)),
        'bh_last_price': float(round(bh_last_price, 2)),
        'bh_final_value': float(round(bh_final_value, 0)),
        'bh_return_pct': float(round(bh_return_pct, 2)),
        'dca_vs_bh': float(round(dca_vs_bh, 2)),
        'period_high': float(round(period_high, 2)),
        'period_low': float(round(period_low, 2)),
        'period_pos': float(round(period_pos, 1))
    }
