# -*- coding: utf-8 -*-
"""Nana v6.5 — 交易失敗模式修正版

根據 901 筆歷史交易分析，發現關鍵問題：

1. 【最大問題】Trailing Stop WR 僅 2.4%，平均虧損 -5.28%
   → 移除或大幅緊縮 trailing stop 邏輯
2. 【次要問題】持有 2-7 天 WR 極低（12-36%）
   → 延長持有期至 10 天
3. 【優點】Take Profit WR 100%，平均 +8.55%
   → 優先使用靜止利

修正策略：
- ATR TP MULT: 4.0x → 5.0x（給更多空間）
- ATR SL MULT: 1.5x → 2.0x（擴大停損容忍）
- HOLD_DAYS: 7 → 10（延長持有）
- TRAILING ATR: 2.0 → 移除（不再使用）
- SCORE_MIN: 32 → 35（提高品質）
"""

import sys, os, json, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

STOCK_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\stock_names.json'
CACHE_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\scan_cache_v65.json'
REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\reports\nana_v65_scan.json'

# ===== PARAMETERS (v6.5 - 修正版) =====
RSI_PERIOD = 12
RSI_ENTRY_MIN = 30   # 擴大範圍（原35）
RSI_ENTRY_MAX = 45
MOMENTUM_MIN = 3.0
ADX_MIN = 18
SCORE_MIN = 35        # 提高門檻（原32）
ATR_TP_MULT = 5.0     # 擴大靜止利空間（原4.0）
ATR_SL_MULT = 2.0    # 擴大停損（原1.5）
HOLD_DAYS = 10        # 延長持有（原7）
TRAILING_ATR = None   # 移除 trail stop（原2.0）

# ===== LOAD STOCKS =====
with open(STOCK_FILE, encoding='utf-8') as f:
    stock_names = json.load(f)
VALID_STOCKS = [s for s in stock_names.keys() if s not in ('2888', '5882')]

# ===== INDICATORS =====
def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 100

def get_ma(closes, period):
    if len(closes) < period:
        return closes[-1]
    return float(np.mean(closes[-period:]))

def get_adx(high, low, close, period=14):
    if len(close) < period + 1:
        return 15.0
    trs = []
    for i in range(1, len(close)):
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        trs.append(tr)
    if len(trs) < period:
        return 15.0
    atr = np.mean(trs[-period:])
    plus_dm = high[i] - high[i - 1] if i > 0 else 0
    minus_dm = low[i - 1] - low[i] if i > 0 else 0
    if plus_dm > minus_dm and plus_dm > 0:
        plus_dm = min(plus_dm, trs[-1]) if trs else 0
        minus_dm = 0
    else:
        minus_dm = min(minus_dm, trs[-1]) if trs else 0
        plus_dm = 0
    avg_plus = np.mean([plus_dm] * period) if period > 0 else 0
    avg_minus = np.mean([minus_dm] * period) if period > 0 else 0
    if avg_minus == 0:
        return 25.0
    return float(np.mean(trs[-period:]) / (atr + 0.0001) * 50)

def get_atr(high, low, close, period=14):
    if len(close) < 2:
        return 5.0
    trs = []
    for i in range(1, len(close)):
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars - 1] - 1) * 100)

# ===== ANALYZE =====
def analyze(symbol):
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='60d')
        if h.empty or len(h) < 30:
            return None

        c = h['Close'].values
        h_arr = h['High'].values
        l_arr = h['Low'].values

        price = float(c[-1])
        rsi = get_rsi(c, RSI_PERIOD)
        mom5 = get_momentum(c, 5)
        ma20 = get_ma(c, 20)
        ma60 = get_ma(c, 60)
        atr = get_atr(h_arr, l_arr, c)
        adx = 20  # Simplified

        pos20 = (price / ma20 - 1) * 100 if ma20 != 0 else 0
        pos60 = (price / ma60 - 1) * 100 if ma60 != 0 else 0

        # Scoring
        score = 0
        if RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX:
            score += 30
        elif rsi < RSI_ENTRY_MIN:
            score += 15
        if mom5 > MOMENTUM_MIN:
            score += 20
        elif mom5 > 2:
            score += 10
        if pos60 > 0:
            score += 15
        if pos20 > 0:
            score += 10
        if adx > ADX_MIN:
            score += 10

        # TP/SL
        tp_price = round(price + ATR_TP_MULT * atr, 2)
        sl_price = round(price - ATR_SL_MULT * atr, 2)

        entry_ok = (
            RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX
            and mom5 > MOMENTUM_MIN
            and adx > ADX_MIN
            and score >= SCORE_MIN
        )

        return {
            'symbol': symbol,
            'name': stock_names.get(symbol, symbol),
            'price': price,
            'rsi': round(rsi, 1),
            'mom5': round(mom5, 1),
            'pos20': round(pos20, 1),
            'pos60': round(pos60, 1),
            'adx': adx,
            'atr': round(atr, 2),
            'score': score,
            'entry': entry_ok,
            'target': tp_price,
            'stop': sl_price,
            'rsi_label': ' OB' if rsi > 70 else (' OS' if rsi < 30 else '')
        }
    except:
        return None

# ===== MAIN =====
print('=' * 60)
print('Nana v6.5 交易失敗模式修正版')
print('Time:', time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

results = []
for i, sym in enumerate(VALID_STOCKS):
    if (i + 1) % 20 == 0:
        print(f'  {i+1}/{len(VALID_STOCKS)}...')
    r = analyze(sym)
    if r:
        results.append(r)

results.sort(key=lambda x: x['score'], reverse=True)
candidates = [r for r in results if r['entry']]

print(f'Scanned: {len(VALID_STOCKS)} | Candidates: {len(candidates)}')
print()
print('CODE   PRICE      RSI    MOM5D   MA60%   SCORE   TARGET    STOP   NAME')
print('-' * 75)
for r in candidates[:15]:
    print('{:<6} {:>9} {:>5}{:>5} {:>+6.1f}% {:>6} {:>9} {:>8} {}'.format(
        r['symbol'], r['price'], r['rsi'], r['rsi_label'],
        r['mom5'], r['pos60'], r['score'], r['target'], r['stop'], r['name']))

print()
print('=== v6.5 修正重點 ===')
print('1. 移除 Trailing Stop（WR 僅 2.4%）')
print('2. 延長持有至 10 天（原 7 天）')
print('3. 擴大靜止利 ATR 5.0x（原 4.0x）')
print('4. 擴大停損 ATR 2.0x（原 1.5x）')
print('5. 提高 SCORE_MIN 至 35（原 32）')

# Save
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump({'timestamp': time.strftime('%Y-%m-%d %H:%M'), 'candidates': candidates}, f, ensure_ascii=False, indent=2)
print()
print('Report saved:', REPORT_FILE)