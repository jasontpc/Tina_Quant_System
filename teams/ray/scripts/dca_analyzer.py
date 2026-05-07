# -*- coding: utf-8 -*-
"""
Ray DCA Analyzer — 單一 ETF DCA 分析引擎（增強版）
用法: python scripts/dca_analyzer.py [ETF代碼] [金額]
例如: python scripts/dca_analyzer.py 00919 5000
"""
import yfinance as yf
import pandas as pd
import sys
import os
import requests
import json
from datetime import datetime, timedelta

# Dynamic path setup so 'teams' package resolves from project root
_ProjRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../teams/ray/scripts -> .../teams/ray -> root
if _ProjRoot not in sys.path:
    sys.path.insert(0, _ProjRoot)

try:
    from teams.team_shared import TeamShared
except ModuleNotFoundError:
    _alt = os.path.dirname(_ProjRoot)
    if _alt not in sys.path:
        sys.path.insert(0, _alt)
    import team_shared as _ts
    TeamShared = _ts.TeamShared

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00881': '國泰台灣5G', '00915': '富邦台灣永續高息',
    '00923': '群益台灣ESG低碳', '00895': '富邦上証', '00762': '元大石油'
}

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
LOG_FILE = os.path.join(REPORTS_DIR, 'dca_analysis_log.json')
RAY_SIGNALS_FILE = 'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\shared\\ray_signals.json'
os.makedirs(REPORTS_DIR, exist_ok=True)


def get_price_history(etf_id, period='1y'):
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
        return r.json().get('data', [])
    except:
        return []


def get_twii_position():
    """取得 TWII 整體位置"""
    try:
        twii = yf.Ticker('^TWII').history(period='1y')['Close']
        price = twii.iloc[-1]
        low = twii.min()
        high = twii.max()
        return (price - low) / (high - low) * 100 if high > low else 50
    except:
        return None


def load_analysis_log():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_analysis_record(record):
    log = load_analysis_log()
    log.append(record)
    log = log[-500:]
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def write_ray_signal(etf_id, signal_data):
    """寫入 Ray 訊號到共享區"""
    try:
        signals = {}
        with open(RAY_SIGNALS_FILE, 'r', encoding='utf-8') as f:
            signals = json.load(f)
    except:
        signals = {}

    signals[etf_id] = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        **signal_data
    }

    with open(RAY_SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)


def analyze_dca(etf_id, monthly_amount=5000):
    """單一ETF DCA 分析"""
    name = ETF_NAMES.get(etf_id, etf_id)
    print(f'\n=== Ray DCA 分析 — {name} ({etf_id}) ===')
    print(f'  定期定額金額: ${monthly_amount:,}')
    print()

    close = get_price_history(etf_id, '1y')
    price = close.iloc[-1]
    price_1y_low = close.min()
    price_1y_high = close.max()
    price_1y_avg = close.mean()
    position_pct = (price - price_1y_low) / (price_1y_high - price_1y_low) * 100 if price_1y_high > price_1y_low else 50

    rsi = calc_rsi(close).iloc[-1]

    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else close.mean()
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    recent_5d = close.tail(5)
    recent_pct = (recent_5d.iloc[-1] / recent_5d.iloc[0] - 1) * 100 if len(recent_5d) >= 2 else 0

    inst_rows = get_institutional(etf_id)
    fi_net = sum(r['buy'] - r['sell'] for r in inst_rows if r['name'] == 'Foreign_Investor')
    it_net = sum(r['buy'] - r['sell'] for r in inst_rows if r['name'] == 'Investment_Trust')
    fi_days = sum(1 for r in inst_rows if r['name'] == 'Foreign_Investor' and r['buy'] - r['sell'] > 0)

    twii_pos = get_twii_position()

    entry_willingness = '積極' if position_pct < 40 else ('普通' if position_pct < 70 else '觀望')
    amount_suggestion = '正常' if position_pct < 60 else ('減少' if position_pct < 80 else '暫停')

    if position_pct < 30:
        entry_rating = '極佳進場點'
    elif position_pct < 50:
        entry_rating = '合理進場點'
    elif position_pct < 70:
        entry_rating = '中性偏高'
    else:
        entry_rating = '昂貴，建議觀望'

    print('【核心判斷】')
    print(f'  進場意願: {entry_willingness}')
    print(f'  建議金額: {amount_suggestion}')
    print(f'  進場評級: {entry_rating}')
    print()
    print('【價值評估】')
    print(f'  目前價格: ${price:.2f}')
    print(f'  近1年區間: ${price_1y_low:.2f} ~ ${price_1y_high:.2f}')
    print(f'  近1年平均: ${price_1y_avg:.2f}')
    print(f'  目前位置: {position_pct:.1f}% (0%=低點, 100%=高點)')
    print()
    print('【技術指標】')
    print(f'  RSI(14): {rsi:.1f}')
    print(f'  MA20: ${ma20:.2f} | 目前{"高於" if price > ma20 else "低於"}MA20')
    print(f'  MA60: ${ma60:.2f} | 目前{"高於" if price > ma60 else "低於"}MA60')
    if ma200:
        print(f'  MA200: ${ma200:.2f} | 目前{"高於" if price > ma200 else "低於"}MA200')
    print(f'  5日走勢: {recent_pct:+.2f}%')
    print()
    print('【法人動態 (近30日)】')
    print(f'  外資淨買: {fi_net//1000000:+d}M ({fi_days}天)')
    print(f'  投信淨買: {it_net//1000000:+d}M')
    print()
    if twii_pos:
        print('【市場情緒】')
        print(f'  TWII 目前位置: {twii_pos:.1f}% (近1年)')
        print()
    print('【風險提示】')
    if position_pct > 70:
        print(f'  ⚠️ 價格處於近1年高點區間，進場成本偏高')
    if rsi > 75:
        print(f'  ⚠️ RSI={rsi:.1f}，市場情緒過熱，短期可能回調')
    if recent_pct > 10:
        print(f'  ⚠️ 5日反彈{recent_pct:.1f}%，適合等拉回再買')
    if fi_net < 0:
        print(f'  ⚠️ 外資近期倒貨({fi_net//1000000}M)，需留意')
    if twii_pos and twii_pos > 80:
        print(f'  ⚠️ TWII 接近歷史高點，整體市場偏高')
    print()
    print('【Ray 建議】')
    action = '買進' if position_pct < 70 else '觀望/等'
    print(f'  行動: {action}')
    print(f'  理由: {entry_rating}，目前價格在近1年區間的{position_pct:.0f}%位置')
    print()

    record = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'etf': etf_id,
        'name': name,
        'price': float(price),
        'position_pct': round(position_pct, 1),
        'rsi': round(rsi, 1),
        'fi_net': int(fi_net),
        'it_net': int(it_net),
        'entry_willingness': entry_willingness,
        'amount_suggestion': amount_suggestion,
        'action': action
    }
    save_analysis_record(record)
    write_ray_signal(etf_id, {
        'position_pct': round(position_pct, 1),
        'entry_willingness': entry_willingness,
        'amount_suggestion': amount_suggestion,
        'action': action,
        'price': float(price)
    })

    return record


if __name__ == '__main__':
    etf_id = sys.argv[1] if len(sys.argv) > 1 else '00919'
    amount = sys.argv[2] if len(sys.argv) > 2 else '5000'
    monthly_amount = int(amount)
    analyze_dca(etf_id, monthly_amount)
