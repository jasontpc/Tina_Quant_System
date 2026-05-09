# -*- coding: utf-8 -*-
"""
Ray Buy&Hold Finder — 進場點評分系統
功能：
  - 針對 15 檔 ETF 分析是否出現 Buy&Hold 進場點
  - 計算相對低點位置、RSI、法人動向
  - 輸出建議報告（強制 BH / 混合 / 純 DCA）
"""
import yfinance as yf
import pandas as pd
import json
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
REPORT_FILE = BASE_DIR / 'reports' / 'buyandhold_finder_report.json'
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

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


def get_kline(etf_id, period='2y'):
    """抓取 K線數據"""
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


def get_institutional(etf_id, lookback=20):
    """抓取法人買賣資料（近N日）"""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': etf_id,
        'start_date': start,
        'end_date': end,
        'token': TOKEN
    }
    try:
        r = requests.get(FINMIND_URL, params=params, timeout=15)
        data = r.json().get('data', [])
        return data
    except:
        return []


def analyze_entry_point(etf_id):
    """
    分析單一 ETF 的 Buy&Hold 進場點
    返回評分結果
    """
    close = get_kline(etf_id, '2y')
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])

    # === 均線計算 ===
    ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
    ma120 = float(close.rolling(120).mean().iloc[-1]) if len(close) >= 120 else None

    # === 低點計算 ===
    low_52w = float(close.rolling(52).min().iloc[-1]) if len(close) >= 52 else float(close.min())
    low_26w = float(close.rolling(26).min().iloc[-1]) if len(close) >= 26 else float(close.min())

    # === 偏離計算 ===
    deviation_low_52w = (price - low_52w) / low_52w * 100 if low_52w != 0 else 0
    deviation_ma120 = (price - ma120) / ma120 * 100 if ma120 and ma120 != 0 else 0

    # === RSI ===
    rsi = float(calc_rsi(close).iloc[-1])

    # === 法人資料 ===
    inst_data = get_institutional(etf_id)
    fi_buy_days = 0  # 外資連續買超天數
    fi_net_total = 0
    for r in inst_data:
        if r.get('name') == 'Foreign_Investor':
            net = r.get('buy', 0) - r.get('sell', 0)
            fi_net_total += net
            if net > 0:
                fi_buy_days += 1

    # === 評分 ===
    score = 0
    details = []

    # 52週低點偏離 < 5% → 5分
    if deviation_low_52w < 5:
        score += 5
        details.append(f'52W低點偏離 {deviation_low_52w:.1f}% (+5分)')
    elif deviation_low_52w < 10:
        score += 3
        details.append(f'52W低點偏離 {deviation_low_52w:.1f}% (+3分)')

    # MA120 偏離 < 5% → 5分
    if ma120 and deviation_ma120 < 5:
        score += 5
        details.append(f'MA120偏離 {deviation_ma120:.1f}% (+5分)')
    elif ma120 and deviation_ma120 < 10:
        score += 3
        details.append(f'MA120偏離 {deviation_ma120:.1f}% (+3分)')

    # RSI < 30 → 5分（超賣）
    if rsi < 30:
        score += 5
        details.append(f'RSI={rsi:.1f} 超賣 (+5分)')
    elif rsi < 40:
        score += 3
        details.append(f'RSI={rsi:.1f} 低檔 (+3分)')
    elif rsi > 70:
        score -= 3
        details.append(f'RSI={rsi:.1f} 過熱 (-3分)')

    # 法人連續買超 ≥ 3天 → 5分
    if fi_buy_days >= 3:
        score += 5
        details.append(f'外援連續買超 {fi_buy_days} 天 (+5分)')
    elif fi_buy_days >= 1:
        score += 2
        details.append(f'外援買超 {fi_buy_days} 天 (+2分)')

    # 額外：位置 < 50%（1年低點區間）→ 額外 +3分
    if len(close) >= 252:
        low_1y = float(close.tail(252).min())
        high_1y = float(close.tail(252).max())
        pos_1y = (price - low_1y) / (high_1y - low_1y) * 100 if high_1y > low_1y else 50
        if pos_1y < 50:
            score += 3
            details.append(f'1年位置 {pos_1y:.1f}% 低點區 (+3分)')

    # === 策略建議 ===
    # 總分 ≥ 15 → 強制 Buy&Hold
    # 總分 10-15 → 50% BH + 50% DCA
    # 總分 < 10 → 純 DCA
    if score >= 15:
        recommendation = 'BUY&HOLD'
        bh_ratio = 1.0
        desc = '強制進場（重大低點）'
    elif score >= 10:
        recommendation = 'HYBRID'
        bh_ratio = 0.5
        desc = '混合策略（中期低點）'
    else:
        recommendation = 'DCA'
        bh_ratio = 0.0
        desc = '正常定期定額'

    # === 建議金額 ===
    base_amount = 10000
    if recommendation == 'BUY&HOLD':
        suggested_amount = 100000  # NT$100,000 一次買入
        amount_note = '一次買入 NT$100,000'
    elif recommendation == 'HYBRID':
        suggested_amount = 50000   # 50% BH = NT$50,000
        amount_note = 'NT$50,000 Buy&Hold + NT$50,000 DCA'
    else:
        suggested_amount = 10000
        amount_note = 'NT$10,000/月 正常 DCA'

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'price': round(price, 2),
        'ma60': round(ma60, 2) if ma60 else None,
        'ma120': round(ma120, 2) if ma120 else None,
        'low_52w': round(low_52w, 2),
        'low_26w': round(low_26w, 2),
        'deviations': {
            'low_52w_pct': round(deviation_low_52w, 2),
            'ma120_pct': round(deviation_ma120, 2)
        },
        'rsi': round(rsi, 1),
        'institutional': {
            'fi_buy_days': fi_buy_days,
            'fi_net_total': int(fi_net_total)
        },
        'score': score,
        'details': details,
        'recommendation': recommendation,
        'bh_ratio': bh_ratio,
        'desc': desc,
        'suggested_amount': suggested_amount,
        'amount_note': amount_note,
        'timestamp': datetime.now().isoformat()
    }


def run_buyandhold_finder():
    """主執行"""
    print('=' * 75)
    print('Ray Buy&Hold Finder — 進場點評分系統')
    print('=' * 75)
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    results = []
    for etf_id in MONITOR_ETFS:
        print(f'分析 {etf_id} ({ETF_NAMES.get(etf_id, etf_id)})...', end=' ')
        r = analyze_entry_point(etf_id)
        if r:
            results.append(r)
            print(f'✓ Score={r["score"]} → {r["recommendation"]} ({r["desc"]})')
        else:
            print(f'✗ 資料不足')

    print()
    print(f'成功分析: {len(results)}/{len(MONITOR_ETFS)} 檔')
    print()

    # === 輸出報告 ===
    print('=' * 75)
    print('【Buy&Hold 進場點評分報告】')
    print('=' * 75)

    # 排序（分數高的在前）
    results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)

    # Buy&Hold
    bh = [r for r in results_sorted if r['recommendation'] == 'BUY&HOLD']
    hy = [r for r in results_sorted if r['recommendation'] == 'HYBRID']
    dca = [r for r in results_sorted if r['recommendation'] == 'DCA']

    if bh:
        print()
        print('■ 【強制 Buy&Hold】Score ≥ 15')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"評分":>5s} {"價格":>7s} {"MA120":>7s} {"52W低偏":>8s} {"RSI":>5s} {"外援天":>6s} {"建議金額"}')
        print('  ' + '-' * 90)
        for r in bh:
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} {r["score"]:>4d}  ${r["price"]:>6.2f} ${r["ma120"] or 0:>6.2f} {r["deviations"]["low_52w_pct"]:>+7.1f}% {r["rsi"]:>5.1f} {r["institutional"]["fi_buy_days"]:>5d}天 {r["amount_note"]}')

    if hy:
        print()
        print('■ 【混合策略】Score 10-14')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"評分":>5s} {"價格":>7s} {"MA120":>7s} {"52W低偏":>8s} {"RSI":>5s} {"外援天":>6s} {"建議金額"}')
        print('  ' + '-' * 90)
        for r in hy:
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} {r["score"]:>4d}  ${r["price"]:>6.2f} ${r["ma120"] or 0:>6.2f} {r["deviations"]["low_52w_pct"]:>+7.1f}% {r["rsi"]:>5.1f} {r["institutional"]["fi_buy_days"]:>5d}天 {r["amount_note"]}')

    if dca:
        print()
        print('■ 【純 DCA】Score < 10')
        print(f'  {"ETF":<8s} {"名稱":<10s} {"評分":>5s} {"價格":>7s} {"1年位置":>8s} {"RSI":>5s} {"說明"}')
        print('  ' + '-' * 60)
        for r in dca:
            pos_1y = 50  # 預設
            print(f'  {r["etf_id"]:<8s} {r["name"]:<10s} {r["score"]:>4d}  ${r["price"]:>6.2f} {pos_1y:>7.1f}% {r["rsi"]:>5.1f} {r["desc"]}')

    print()
    print('【評分說明】')
    print('  • 52週低點偏離 < 5% → +5分（極佳）')
    print('  • MA120 偏離 < 5% → +5分（極佳）')
    print('  • RSI < 30 → +5分（超賣）')
    print('  • 外援連續買超 ≥ 3天 → +5分')
    print('  • 1年位置 < 50% → +3分（額外）')
    print()
    print('【策略說明】')
    print('  • 強制 Buy&Hold：低點一次買入 NT$100,000，設定目標價 +20%，停損 -15%')
    print('  • 混合策略：50% BH (NT$50,000) + 50% DCA (NT$10,000/月)')
    print('  • 純 DCA：維持正常 NT$10,000/月定期定額')
    print()

    # === 總結建議 ===
    print('【Ray 建議摘要】')
    if bh:
        names = ', '.join([f'{r["name"]}({r["etf_id"]})' for r in bh])
        total_amount = sum(r['suggested_amount'] for r in bh)
        print(f'  強制 Buy&Hold ({len(bh)} 檔): {names}')
        print(f'  建議總金額: NT${total_amount:,}')
    if hy:
        names = ', '.join([f'{r["name"]}({r["etf_id"]})' for r in hy])
        print(f'  混合策略 ({len(hy)} 檔): {names}')
    if dca:
        print(f'  純 DCA ({len(dca)} 檔): 維持正常定期定額')

    # === 儲存 ===
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print()
    print(f'報告已儲存: {REPORT_FILE}')

    return results


if __name__ == '__main__':
    run_buyandhold_finder()