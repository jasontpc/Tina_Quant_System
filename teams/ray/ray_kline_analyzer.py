# -*- coding: utf-8 -*-
"""
Ray K線分析模組 — 識別相對低點與進場點
功能：
  - 抓取 ETF K線數據（OHLCV）
  - 計算均線（MA20/MA60/MA120）
  - 識別相對低點（52週/26週/12週）
  - 判斷 Buy&Hold vs DCA 進場策略
"""
import yfinance as yf
import pandas as pd
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')

# 15檔監控ETF
MONITOR_ETFS = [
    '0050', '0056', '00878', '00891', '00919',
    '00927', '00713', '00646', '00662', '00757',
    '00923', '00915', '00917', '00918', '00920'
]

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00923': '凱基優選高股息', '00915': '兆豐永續高息',
    '00917': '中信關鍵半導體', '00918': '中信上游半導體', '00920': '中信特選金融'
}


def get_kline_data(etf_id, period='2y'):
    """抓取 ETF K線數據（包含 OHLCV）"""
    sym = etf_id + '.TW'
    h = yf.Ticker(sym).history(period=period, auto_adjust=False)
    # 確保 Close 是 Series
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    h['Close'] = close
    return h


def calc_moving_averages(close):
    """計算 MA20, MA60, MA120"""
    ma20 = close.rolling(20).mean() if len(close) >= 20 else None
    ma60 = close.rolling(60).mean() if len(close) >= 60 else None
    ma120 = close.rolling(120).mean() if len(close) >= 120 else None
    return ma20, ma60, ma120


def calc_rsi(close, period=14):
    """計算 RSI(14)"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def identify_relative_lows(close):
    """
    識別相對低點
    - 52週低點（~1年）
    - 26週低點（~半年）
    - 12週低點（~3個月）
    """
    results = {}

    # 52週低點（252個交易日）
    if len(close) >= 52:
        low_52w = close.rolling(52).min()
        results['low_52w'] = float(low_52w.iloc[-1])
        results['low_52w_date'] = str(close.iloc[-252:].idxmin().date()) if len(close) >= 252 else None
    else:
        results['low_52w'] = float(close.min())
        results['low_52w_date'] = None

    # 26週低點（126個交易日）
    if len(close) >= 26:
        low_26w = close.rolling(26).min()
        results['low_26w'] = float(low_26w.iloc[-1])
    else:
        results['low_26w'] = float(close.min())

    # 12週低點（60個交易日）
    if len(close) >= 12:
        low_12w = close.rolling(12).min()
        results['low_12w'] = float(low_12w.iloc[-1])
    else:
        results['low_12w'] = float(close.min())

    return results


def calc_support_resistance(close, lookback=60):
    """計算支撐位與阻力位（近60日）"""
    if len(close) < lookback:
        lookback = len(close)

    recent = close.tail(lookback)
    low = float(recent.min())
    high = float(recent.max())
    avg = float(recent.mean())

    # 支撐：低點 + 15%區間
    # 阻力：高點 - 15%區間
    range_pct = (high - low) * 0.15

    return {
        'support_1': round(low, 2),
        'support_2': round(low + range_pct, 2),
        'resistance_1': round(high - range_pct, 2),
        'resistance_2': round(high, 2),
        'mid_point': round((high + low) / 2, 2)
    }


def determine_strategy(price, ma60, ma120, low_52w, low_26w):
    """
    根據價格相對均線位置判斷策略
    規則：
      - 價格 < MA120 → 強制 Buy&Hold
      - 價格在 MA60-120 之間 → 50% Buy&Hold + 50% DCA
      - 價格 > MA60 → 純 DCA
    """
    # 計算偏離
    ma60_dev = (price - ma60) / ma60 * 100 if ma60 and ma60 != 0 else 0
    ma120_dev = (price - ma120) / ma120 * 100 if ma120 and ma120 != 0 else 0
    low_52w_dev = (price - low_52w) / low_52w * 100 if low_52w and low_52w != 0 else 0
    low_26w_dev = (price - low_26w) / low_26w * 100 if low_26w and low_26w != 0 else 0

    # 進場信號
    signal_major_low = low_52w_dev < 5      # 觸及52週低點
    signal_mid_low = low_26w_dev < 5         # 觸及26週低點
    signal_below_ma120 = price < ma120 if ma120 else False
    signal_below_ma60 = price < ma60 if ma60 else False

    # 策略判定
    if signal_below_ma120:
        strategy = 'BUY&HOLD'
        bh_ratio = 1.0
        reason = f'價格 ${price:.2f} < MA120 ${ma120:.2f}，長期低點，強制 Buy&Hold'
    elif ma60 and price < ma60:
        strategy = 'HYBRID_50'
        bh_ratio = 0.5
        reason = f'價格 ${price:.2f} < MA60 ${ma60:.2f}，中期低點，50% Buy&Hold + 50% DCA'
    else:
        strategy = 'DCA'
        bh_ratio = 0.0
        reason = f'價格 ${price:.2f} > MA60 ${ma60:.2f}，正常區間，純 DCA'

    # 低點強度
    if signal_major_low:
        low_strength = '極強（52週低點）'
    elif signal_mid_low:
        low_strength = '強（26週低點）'
    else:
        low_strength = '普通'

    return {
        'strategy': strategy,
        'bh_ratio': bh_ratio,
        'dca_ratio': 1.0 - bh_ratio,
        'reason': reason,
        'low_strength': low_strength,
        'signals': {
            'major_low_52w': signal_major_low,
            'mid_low_26w': signal_mid_low,
            'below_ma120': signal_below_ma120,
            'below_ma60': signal_below_ma60
        },
        'deviations': {
            'ma60_pct': round(ma60_dev, 2),
            'ma120_pct': round(ma120_dev, 2),
            'low_52w_pct': round(low_52w_dev, 2),
            'low_26w_pct': round(low_26w_dev, 2)
        }
    }


def analyze_etf_kline(etf_id):
    """分析單一 ETF 的 K線結構"""
    try:
        kline = get_kline_data(etf_id, '2y')
        close = kline['Close'].squeeze() if isinstance(kline['Close'], pd.DataFrame) else kline['Close']
        kline['Close'] = close

        if len(close) < 60:
            return None

        price = float(close.iloc[-1])

        # 均線
        ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
        ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
        ma120 = float(close.rolling(120).mean().iloc[-1]) if len(close) >= 120 else None

        # 相對低點
        lows = identify_relative_lows(close)

        # 支撐/阻力
        sr = calc_support_resistance(close)

        # RSI
        rsi = float(calc_rsi(close).iloc[-1])

        # 策略判定
        strategy = determine_strategy(
            price,
            ma60 if ma60 else 0,
            ma120 if ma120 else 0,
            lows['low_52w'],
            lows['low_26w']
        )

        # 1年位置
        year_low = float(close.tail(252).min()) if len(close) >= 252 else lows['low_52w']
        year_high = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
        position_pct = (price - year_low) / (year_high - year_low) * 100 if year_high > year_low else 50

        return {
            'etf_id': etf_id,
            'name': ETF_NAMES.get(etf_id, etf_id),
            'price': round(price, 2),
            'ma20': round(ma20, 2) if ma20 else None,
            'ma60': round(ma60, 2) if ma60 else None,
            'ma120': round(ma120, 2) if ma120 else None,
            'lows': {
                '52w': round(lows['low_52w'], 2),
                '26w': round(lows['low_26w'], 2),
                '12w': round(lows['low_12w'], 2),
                '52w_date': lows.get('low_52w_date')
            },
            'support_resistance': sr,
            'rsi': round(rsi, 1),
            'position_1y_pct': round(position_pct, 1),
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {'etf_id': etf_id, 'error': str(e)}


def analyze_all_etfs():
    """分析所有 15 檔 ETF"""
    print('=== Ray K線分析 — 15檔ETF ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    results = []
    for etf_id in MONITOR_ETFS:
        print(f'分析 {etf_id} ({ETF_NAMES.get(etf_id, etf_id)})...', end=' ')
        r = analyze_etf_kline(etf_id)
        if r and 'error' not in r:
            results.append(r)
            s = r['strategy']
            print(f'✓ {s["strategy"]} (MA120偏離: {s["deviations"]["ma120_pct"]:+.1f}%)')
        else:
            print(f'✗ {r.get("error", "失敗")}')

    print()
    print(f'成功分析: {len(results)}/{len(MONITOR_ETFS)} 檔')
    return results


def print_analysis(results):
    """輸出分析報告"""
    print()
    print('=' * 75)
    print('【Ray K線分析報告 — Buy&Hold vs DCA 進場點】')
    print('=' * 75)

    # 按策略分組
    bh_etfs = [r for r in results if r['strategy']['strategy'] == 'BUY&HOLD']
    hybrid = [r for r in results if r['strategy']['strategy'] == 'HYBRID_50']
    dca_etfs = [r for r in results if r['strategy']['strategy'] == 'DCA']

    if bh_etfs:
        print()
        print('■ 【強制 Buy&Hold】— 價格 < MA120，長期低點')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"價格":>7s} {"MA120":>7s} {"偏離%":>7s} {"52W低點":>8s} {"偏離%":>7s} {"RSI":>5s} {"強度":>10s}')
        print('  ' + '-' * 78)
        for r in bh_etfs:
            dev = r['strategy']['deviations']
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} ${r["price"]:>6.2f} ${r["ma120"] or 0:>6.2f} {dev["ma120_pct"]:>+6.1f}% {r["lows"]["52w"]:>7.2f} {dev["low_52w_pct"]:>+6.1f}% {r["rsi"]:>5.1f} {r["strategy"]["low_strength"]:<10s}')

    if hybrid:
        print()
        print('■ 【50% Buy&Hold + 50% DCA】— 價格在 MA60-MA120 之間')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"價格":>7s} {"MA60":>7s} {"偏離%":>7s} {"MA120":>7s} {"偏離%":>7s} {"RSI":>5s}')
        print('  ' + '-' * 65)
        for r in hybrid:
            dev = r['strategy']['deviations']
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} ${r["price"]:>6.2f} ${r["ma60"] or 0:>6.2f} {dev["ma60_pct"]:>+6.1f}% ${r["ma120"] or 0:>6.2f} {dev["ma120_pct"]:>+6.1f}% {r["rsi"]:>5.1f}')

    if dca_etfs:
        print()
        print('■ 【純 DCA】— 價格 > MA60')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"價格":>7s} {"MA60":>7s} {"偏離%":>7s} {"1年位置":>8s} {"RSI":>5s}')
        print('  ' + '-' * 55)
        for r in dca_etfs:
            dev = r['strategy']['deviations']
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} ${r["price"]:>6.2f} ${r["ma60"] or 0:>6.2f} {dev["ma60_pct"]:>+6.1f}% {r["position_1y_pct"]:>7.1f}% {r["rsi"]:>5.1f}')

    print()
    print('【說明】')
    print('  MA120偏離% = (目前價格 - MA120) / MA120 * 100')
    print('  52W低點偏離% = (目前價格 - 52週低點) / 52週低點 * 100')
    print('  RSI < 30 = 超賣區，強烈 Buy&Hold 信號')
    print()

    # 總結
    print('【Ray 建議】')
    if bh_etfs:
        names = ', '.join([f'{r["name"]}({r["etf_id"]})' for r in bh_etfs])
        print(f'  Buy&Hold 強制進場: {names}')
    if hybrid:
        names = ', '.join([f'{r["name"]}({r["etf_id"]})' for r in hybrid])
        print(f'  混合策略（50% BH）: {names}')
    if dca_etfs:
        print(f'  純 DCA: {len(dca_etfs)} 檔維持定期定額')

    return results


def save_results(results, filepath=None):
    """儲存分析結果到 JSON"""
    if filepath is None:
        filepath = BASE_DIR / 'reports' / 'kline_analysis.json'
    filepath.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'結果已儲存: {filepath}')


def run_kline_analyzer():
    """主執行"""
    results = analyze_all_etfs()
    print_analysis(results)
    save_results(results)
    return results


if __name__ == '__main__':
    run_kline_analyzer()