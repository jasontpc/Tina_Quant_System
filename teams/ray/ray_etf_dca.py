# -*- coding: utf-8 -*-
"""
Ray — 台股ETF定期定額分析工具（增強版）
功能：
  - 單一ETF DCA分析
  - 同類ETF比較（0050 vs 0056哪個相對便宜）
  - 建議金額計算（根據近1年位置推薦50%/正常%/100%）

使用說明: python ray_etf_dca.py [ETF代碼] [金額]
例如: python ray_etf_dca.py 00919 5000
       python ray_etf_dca.py 00919 5000 --compare
"""
import yfinance as yf
import pandas as pd
import sys
import os
import requests
import json
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

# ETF名稱對照表
ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00902': '富邦台美菁股'
}

# 同類ETF分組（用於比較）
ETF_GROUPS = {
    '0050': ['0050', '00646'],                         # 台股大型股
    '0056': ['0056', '00878', '00919', '00713'],       # 高股息
    '00891': ['00891', '00923', '00915'],              # 低碳/ESG
    '00662': ['00662', '00757', '00902'],              # 科技/納指/台美菁
}


def get_price_history(etf_id, period='1y'):
    """抓取近1年價格"""
    sym = etf_id + '.TW'
    h = yf.Ticker(sym).history(period=period)
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    return close


def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def get_institutional(etf_id, lookback=30):
    """抓法人資料"""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': etf_id,
        'start_date': start,
        'end_date': end,
        'token': TOKEN
    }
    r = requests.get(FINMIND_URL, params=params, timeout=15)
    return r.json().get('data', [])


def get_etf_value_metrics(etf_id):
    """取得單一ETF的價值評估指標"""
    close = get_price_history(etf_id, '1y').dropna()
    price = float(close.iloc[-1])
    low = close.min()
    high = close.max()
    avg = close.mean()
    position_pct = (price - low) / (high - low) * 100 if high > low else 50

    rsi = calc_rsi(close).iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else close.mean()

    return {
        'price': float(price),
        'low': float(low),
        'high': float(high),
        'avg': float(avg),
        'position_pct': round(position_pct, 1),
        'rsi': round(float(rsi), 1),
        'ma20': float(ma20),
        'ma60': float(ma60)
    }


def compare_similar_etfs(etf_id, base_amount=5000):
    """
    與同類ETF比較，輸出相對便宜的標的
    """
    group = ETF_GROUPS.get(etf_id, [etf_id])
    if etf_id not in group:
        group = [etf_id]

    print()
    print('【同類ETF比較】')
    print(f'  比較組: {", ".join(ETF_NAMES.get(e, e) for e in group)}')
    print()
    dash_etf = '-' * 14
    dash_price = '-' * 8
    dash_low = '-' * 8
    dash_high = '-' * 8
    dash_pos = '-' * 8
    dash_rsi = '-' * 6
    dash_rec = '-' * 6
    print(f'  {"ETF":<14s} {"價格":>8s} {"1年低":>8s} {"1年高":>8s} {"位置%":>8s} {"RSI":>6s}  {"建議"}')
    print(f'  {dash_etf} {dash_price} {dash_low} {dash_high} {dash_pos} {dash_rsi}  {dash_rec}')

    results = []
    for eid in group:
        try:
            m = get_etf_value_metrics(eid)
            entry = '積極買' if m['position_pct'] < 40 else ('普通' if m['position_pct'] < 60 else '觀望')
            print(f'  {ETF_NAMES.get(eid, eid):<12s} ${m["price"]:>7.2f} ${m["low"]:>7.2f} ${m["high"]:>7.2f} {m["position_pct"]:>7.1f}% {m["rsi"]:>5.1f}  {entry}')
            results.append((eid, m['position_pct'], m['price']))
        except Exception as ex:
            print(f'  {eid}: 取得失敗 ({ex})')

    if len(results) < 2:
        print('  （同組無足夠數據进行比较）')
        return None

    # 找出最便宜的（同組位置最低）
    results.sort(key=lambda x: x[1])
    cheapest = results[0]

    print()
    if cheapest[0] == etf_id:
        print(f'  ✓ {ETF_NAMES.get(etf_id, etf_id)} 在同組中最便宜（位置 {cheapest[1]:.1f}%）')
    else:
        print(f'  ⚠️ {ETF_NAMES.get(etf_id, etf_id)} 位置 {get_etf_value_metrics(etf_id)["position_pct"]:.1f}%，')
        print(f'    比 {ETF_NAMES.get(cheapest[0], cheapest[0])} 位置 {cheapest[1]:.1f}% 貴，建議比較後再買')

    return results


def calc_dca_score(position_pct, rsi, fi_net, it_net, recent_pct):
    """
    計算 DCA 價值分數 (0-100)
    愈低價、機構支持、愈值得 DCA
    """
    score = 50
    # 位置越低分數越高 (權重 40%)
    score += (50 - position_pct) * 0.5
    # 外資 (權重 20%)
    fi = fi_net / 1000000
    if fi > 0:
        score += min(fi, 500) * 0.02
    elif fi < -200:
        score -= 5
    # 投信 (權重 10%)
    it = it_net / 1000000
    if it > 0:
        score += min(it, 200) * 0.025
    # RSI (權重 15%)
    if rsi < 40:
        score += 10
    elif rsi < 50:
        score += 5
    elif rsi > 75:
        score -= 5
    # 近期表現 (權重 15%)
    if recent_pct < -5:
        score += 7.5
    elif recent_pct < -2:
        score += 4
    elif recent_pct > 10:
        score -= 5
    return max(0, min(100, round(score, 1)))


def calc_recommended_amount(position_pct, base_amount=5000):
    """
    根據近1年位置計算建議金額
    position_pct: 0% = 低點, 100% = 高點
    返回: (建議金額, 等級, 說明)
    """
    if position_pct < 30:
        return base_amount, '積極(+50%)', f'極佳進場點（位置{position_pct:.1f}%），建議加倍投入'
    elif position_pct < 50:
        return base_amount, '正常(100%)', f'合理進場點（位置{position_pct:.1f}%），正常定期定額'
    elif position_pct < 30:
        return int(base_amount * 0.5), '減少(-50%)', f'中性偏高（位置{position_pct:.1f}%），建議減半'
    else:
        return 0, '觀望(暫停)', f'價格偏高（位置{position_pct:.1f}%），建議觀望'



def analyze_kline_low_points(ticker, period='1y'):
    """
    分析 K線相對低點，計算 DCA 倍數
    1. 抓取 52週、26週、12週低點
    2. 計算目前價格與各低點的偏離%
    3. 給出 DCA 倍數建議

    返回: dict 含 current_price, lows, deviations, dca_multiplier, recommendation
    """
    try:
        sym = ticker + '.TW'
        h = yf.Ticker(sym).history(period=period)
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']

        if len(close) < 60:
            return {'ticker': ticker, 'error': '數據不足'}

        current_price = float(close.dropna().iloc[-1])

        # 52週低點（252個交易日）
        if len(close) >= 252:
            low_52w = float(close.tail(252).min())
        else:
            low_52w = float(close.min())


        # 26週低點（126個交易日）
        if len(close) >= 126:
            low_26w = float(close.tail(126).min())
        else:
            low_26w = float(close.min())

        # 12週低點（60個交易日）
        if len(close) >= 60:
            low_12w = float(close.tail(60).min())
        else:
            low_12w = float(close.min())

        # 偏離計算
        deviation_52w = round((current_price - low_52w) / low_52w * 100, 2) if low_52w > 0 else 0
        deviation_26w = round((current_price - low_26w) / low_26w * 100, 2) if low_26w > 0 else 0
        deviation_12w = round((current_price - low_12w) / low_12w * 100, 2) if low_12w > 0 else 0

        # DCA 倍數判定（優先級：52W > 26W > 12W）
        if deviation_52w < 5:
            dca_multiplier = 2.0
            recommendation = '積極DCA (2倍)'
        elif deviation_26w < 5:
            dca_multiplier = 1.5
            recommendation = '加強DCA (1.5倍)'
        elif deviation_12w < 5:
            dca_multiplier = 1.2
            recommendation = '正常DCA (1.2倍)'
        elif deviation_52w > 20:
            dca_multiplier = 0.5
            recommendation = '觀望 (-50%)'
        else:
            dca_multiplier = 1.0
            recommendation = '正常DCA (1倍)'

        return {
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'low_52w': round(low_52w, 2),
            'low_26w': round(low_26w, 2),
            'low_12w': round(low_12w, 2),
            'deviation_52w': deviation_52w,
            'deviation_26w': deviation_26w,
            'deviation_12w': deviation_12w,
            'dca_multiplier': dca_multiplier,
            'recommendation': recommendation,
            'name': ETF_NAMES.get(ticker, ticker)
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}



def print_kline_analysis(ticker):
    """輸出 K線低點分析報告"""
    result = analyze_kline_low_points(ticker)
    if 'error' in result:
        print(f'分析失敗: {result["error"]}')
        return result

    print(f'=== K線低點分析 — {result["name"]} ({ticker}) ===')
    print()
    print(f'【目前價格】${result["current_price"]:.2f}')
    print()
    print(f'【相對低點】')
    print(f'  52週低點: ${result["low_52w"]:.2f}  → 偏離 {result["deviation_52w"]:+.2f}%')
    print(f'  26週低點: ${result["low_26w"]:.2f}  → 偏離 {result["deviation_26w"]:+.2f}%')
    print(f'  12週低點: ${result["low_12w"]:.2f}  → 偏離 {result["deviation_12w"]:+.2f}%')
    print()
    print(f'【DCA 建議】')
    print(f'  倍數: ×{result["dca_multiplier"]}')
    print(f'  等級: {result["recommendation"]}')
    return result


def analyze_dca(etf_id, monthly_amount=5000, do_compare=False):
    """定期定額分析"""
    name = ETF_NAMES.get(etf_id, etf_id)
    print(f'=== Ray ETF定期定額評估 — {name} ({etf_id}) ===')
    print()

    # 價格資料
    close = get_price_history(etf_id, '1y')
    price = close.iloc[-1]
    price_1y_low = close.min()
    price_1y_high = close.max()
    price_1y_avg = close.mean()
    position_pct = (price - price_1y_low) / (price_1y_high - price_1y_low) * 100 if price_1y_high > price_1y_low else 50

    # RSI
    rsi = calc_rsi(close).iloc[-1]

    # MA
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else close.mean()
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.mean()

    # 近期價格動態
    recent_5d = close.tail(5)
    recent_pct = (recent_5d.iloc[-1] / recent_5d.iloc[0] - 1) * 100

    # 法人資料
    inst_rows = get_institutional(etf_id)
    fi_net = sum(r['buy'] - r['sell'] for r in inst_rows if r['name'] == 'Foreign_Investor')
    it_net = sum(r['buy'] - r['sell'] for r in inst_rows if r['name'] == 'Investment_Trust')
    fi_days = sum(1 for r in inst_rows if r['name'] == 'Foreign_Investor' and r['buy'] - r['sell'] > 0)

    # 進場意願
    entry_willingness = '積極' if position_pct < 30 else ('普通' if position_pct < 30 else '觀望')

    # 進場評級
    if position_pct < 30:
        entry_rating = '極佳進場點'
    elif position_pct < 50:
        entry_rating = '合理進場點'
    elif position_pct < 30:
        entry_rating = '中性偏高'
    else:
        entry_rating = '昂貴，建議觀望'

    # 建議金額
    rec_amount, rec_grade, rec_reason = calc_recommended_amount(position_pct, monthly_amount)

    print(f'【核心判斷】')
    print(f'進場意願: {entry_willingness}')
    print(f'建議等級: {rec_grade}')
    print(f'建議金額: ${rec_amount:,}/月')
    print(f'進場評級: {entry_rating}')
    print()
    print(f'【價值評估】')
    print(f'目前價格: ${price:.2f}')
    print(f'近1年區間: ${price_1y_low:.2f} ~ ${price_1y_high:.2f}')
    print(f'近1年平均: ${price_1y_avg:.2f}')
    print(f'目前位置: {position_pct:.1f}% (0%=低點, 100%=高點)')
    print()
    print(f'【技術指標】')
    print(f'RSI(14): {rsi:.1f}')
    print(f'MA20: ${ma20:.2f} | 目前價格{"高於" if price > ma20 else "低於"}MA20')
    print(f'MA60: ${ma60:.2f} | 目前價格{"高於" if price > ma60 else "低於"}MA60')
    if len(close) >= 200:
        print(f'MA200: ${ma200:.2f} (如果有)')
    print(f'5日走勢: {recent_pct:+.2f}%')
    print()
    print(f'【法人動態 (近30日)】')
    print(f'外援淨買: {fi_net//1000000:+d}M ({fi_days}天)')
    print(f'投信淨買: {it_net//1000000:+d}M')
    print()
    print(f'【風險提示】')
    if position_pct > 70:
        print(f'⚠️ 價格處於近1年高點區間，進場成本偏高')
    if rsi > 75:
        print(f'⚠️ RSI={rsi:.1f}，市場情緒過熱，短期可能回調')
    if recent_pct > 10:
        print(f'⚠️ 5日反彈{recent_pct:.1f}%，適合等拉回再買')
    if fi_net < 0:
        print(f'⚠️ 外資近期倒貨({fi_net//1000000}M)，需留意')
    print()
    print(f'【Ray建議】')
    print(f'行動: {"買進" if position_pct < 30 else "觀望/等"}')
    print(f'理由: {entry_rating}，目前價格在近1年區間的{position_pct:.0f}%位置')

    # DCA Score
    score = calc_dca_score(position_pct, rsi, fi_net, it_net, recent_pct)
    print(f'DCA Score: {score} (0-100, 越高越推薦 DCA)')

    # 同類ETF比較
    if do_compare:
        compare_similar_etfs(etf_id, monthly_amount)

    print()
    print(f'【建議金額說明】')
    print(f'  {rec_reason}')
    print()


if __name__ == '__main__':
    etf_id = sys.argv[1] if len(sys.argv) > 1 else '00919'
    amount = sys.argv[2] if len(sys.argv) > 2 else '5000'
    monthly_amount = int(amount)
    do_compare = '--compare' in sys.argv
    use_kline = '--kline' in sys.argv

    if use_kline:
        print_kline_analysis(etf_id)
    else:
        analyze_dca(etf_id, monthly_amount, do_compare)
