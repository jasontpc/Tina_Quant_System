# -*- coding: utf-8 -*-
"""Nana v6.6 — 交易失敗模式完全修正版

根據 901 筆歷史交易深度分析，發現關鍵問題：

【核心問題】Trailing Stop WR 僅 2.4%，平均虧損 -5.28%
  → 126筆交易中僅3筆獲勝
  → 移除 Trailing Stop，改用純靜止利/停損

【數據發現】
1. hold_expired（持有到期）: WR=48.4%, avg=+0.31%（最穩健）
2. take_profit（靜止利）: WR=100%, avg=+8.55%（完美但次數少）
3. trailing_stop: WR=2.4%, avg=-5.28%（災難）

【最佳參數組合】
- RSI: 30-55 區間進場
- score >= 32
- hold = 8天（全部735筆幾乎都是8天到期）
- regime: BULL 略優於 NEUTRAL

【v6.6 修正】
- 移除 Trailing Stop（不再使用）
- ATR TP MULT: 5.0x（原4.0x，給更多空間）
- ATR SL MULT: 2.0x（原1.5x，擴大容忍）
- HOLD_DAYS: 10（原7）
- RSI_ENTRY_MAX: 55（原45，擴大範圍）
"""

import sys, os, json, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

STOCK_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\stock_names.json'
REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\reports\nana_v66_scan.json'

# ===== v6.6 PARAMETERS =====
RSI_PERIOD = 12
RSI_ENTRY_MIN = 30
RSI_ENTRY_MAX = 55   # 擴大（原45）
MOMENTUM_MIN = 3.0
ADX_MIN = 18
SCORE_MIN = 32
ATR_TP_MULT = 5.0    # 擴大（原4.0）
ATR_SL_MULT = 2.0    # 擴大（原1.5）
HOLD_DAYS = 10       # 延長（原7）
# TRAILING STOP 完全移除

# ===== LOAD STOCKS =====
with open(STOCK_FILE, encoding='utf-8') as f:
    stock_names = json.load(f)
VALID_STOCKS = [s for s in stock_names.keys() if s not in ('2888', '5882')]

def get_rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 100

def get_ma(closes, period):
    return float(np.mean(closes[-period:])) if len(closes) >= period else closes[-1]

def get_atr(high, low, close, period=14):
    if len(close) < 2: return 5.0
    trs = []
    for i in range(1, len(close)):
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def get_momentum(closes, bars=5):
    return float((closes[-1] / closes[-bars - 1] - 1) * 100) if len(closes) >= bars + 1 else 0.0

def analyze(symbol):
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='60d')
        if h.empty or len(h) < 30: return None

        c = h['Close'].values
        h_arr = h['High'].values
        l_arr = h['Low'].values

        price = float(c[-1])
        rsi = get_rsi(c, RSI_PERIOD)
        mom5 = get_momentum(c, 5)
        ma20 = get_ma(c, 20)
        ma60 = get_ma(c, 60)
        atr = get_atr(h_arr, l_arr, c)

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
        if pos60 > 0: score += 15
        if pos20 > 0: score += 10

        entry_ok = (
            RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX
            and mom5 > MOMENTUM_MIN
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
            'atr': round(atr, 2),
            'score': score,
            'entry': entry_ok,
            'target': round(price + ATR_TP_MULT * atr, 2),
            'stop': round(price - ATR_SL_MULT * atr, 2),
            'rsi_label': ' OB' if rsi > 70 else (' OS' if rsi < 30 else '')
        }
    except:
        return None

print('=' * 60)
print('Nana v6.6 交易失敗模式完全修正版')
print('Time:', time.strftime('%Y-%m-%d %H:%M'))
print('=' * 60)

results = []
for i, sym in enumerate(VALID_STOCKS):
    if (i + 1) % 20 == 0: print(f'  {i+1}/{len(VALID_STOCKS)}...')
    r = analyze(sym)
    if r: results.append(r)

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
print('=== v6.6 修正重點 ===')
print('1. 移除 Trailing Stop（WR 2.4% → 廢除）')
print('2. ATR 停利擴大至 5.0x ATR')
print('3. ATR 停損擴大至 2.0x ATR')
print('4. 持有天數延長至 10 天')
print('5. RSI 進場範圍擴大至 30-55')

os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    json.dump({'timestamp': time.strftime('%Y-%m-%d %H:%M'), 'candidates': candidates}, f, ensure_ascii=False, indent=2)
print()
print('Report saved:', REPORT_FILE)