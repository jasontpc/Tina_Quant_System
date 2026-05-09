# -*- coding: utf-8 -*-
"""
Tina Cron v2 — 五大層全面升級版
每週一至週五 16:30 自動執行
涵蓋：L1目標 | L2風控 | L3持倉計時器 | L4市場 | L5行動分級
"""
import sys, json, os, time, sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

# ─── 路徑設定 ───
BASE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(BASE, 'data')
POSITIONS_FILE = os.path.join(DATA_DIR, 'position_tracker.json')
DB = os.path.join(DATA_DIR, 'master_backtest.db')
OUTPUT = os.path.join(BASE, 'stores', 'short_term', 'tina_cron_v2_output.json')

# ─── FinMind Token ───
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'
FINMIND_BASE = 'https://api.finmindtrade.com/api/v4/data'

# ─── 持股期間門檻 ───
HOLD_WARN_DAYS = 20
HOLD_REVIEW_DAYS = 25
HOLD_FORCE_DAYS = 30

# ─── RSI 風控門檻 ───
RSI_NEW_BAN = 75          # 禁止開新倉
RSI_REDUCE_25 = 80        # 降 25%
RSI_REDUCE_50 = 85        # 降 50%
RSI_EXIT = 90             # 全出考慮

# ─── 輔助函式 ───

def get_rsi(c, p=12):
    if len(c) < p + 1:
        return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

def fetch_yf(symbol, period='6mo'):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period=period)
        if h.empty:
            t = yf.Ticker(symbol + '.TW')
            h = t.history(period=period)
        return h
    except:
        return None

def fetch_finmind(dataset, symbol, start_date, end_date):
    params = {
        'dataset': dataset,
        'data_id': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'token': FINMIND_TOKEN,
    }
    try:
        import urllib.request
        import urllib.parse
        url = FINMIND_BASE + '?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success'):
                return data.get('data', [])
    except:
        pass
    return None

def get_twii_rsi():
    h = fetch_yf('^TWII', '60d')
    if h is None or h.empty:
        return None
    c = h['Close'].values
    rsi = get_rsi(c, 14)
    ma20 = np.mean(c[-20:]) if len(c) >= 20 else c[-1]
    ma60 = np.mean(c[-60:]) if len(c) >= 60 else c[-1]
    return {
        'rsi': round(float(rsi), 1),
        'price': round(float(c[-1]), 2),
        'ma20': round(float(ma20), 2),
        'ma60': round(float(ma60), 2),
        'ma_signal': 'bullish' if ma20 > ma60 else 'bearish' if ma20 < ma60 else 'neutral'
    }

def get_vix():
    try:
        h = fetch_yf('^VIX', '20d')
        if h is None or h.empty:
            return None
        return round(float(h['Close'].values[-1]), 2)
    except:
        return None

def get_institutional_flow():
    """抓三大法人買賣超（近3天）"""
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    three_days_ago = (datetime.today() - timedelta(days=4)).strftime('%Y-%m-%d')
    data = fetch_finmind('TaiwanStockInstitutionalInvestorsBuySell', 'TWSE', three_days_ago, yesterday)
    if not data:
        return None
    recent = data[-3:] if len(data) >= 3 else data
    total_buy = sum(d.get('buy', 0) for d in recent)
    total_sell = sum(d.get('sell', 0) for d in recent)
    net = total_buy - total_sell
    return {
        'net': net,
        'days': len(recent),
        'signal': 'bullish' if net > 0 else 'bearish' if net < 0 else 'neutral'
    }

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get('positions', [])
            return data
    return []

def calc_market_sentiment(twii_data, vix, inst_flow):
    """市場情緒分 0-100"""
    score = 50
    if twii_data:
        rsi = twii_data['rsi']
        if rsi < 30: score += 20
        elif rsi < 40: score += 15
        elif rsi < 50: score += 10
        elif rsi < 60: score += 5
        elif rsi < 70: score -= 5
        elif rsi < 80: score -= 15
        elif rsi < 90: score -= 25
        else: score -= 35
    if vix:
        if vix < 15: score += 10
        elif vix > 25: score -= 15
        elif vix > 20: score -= 5
    if inst_flow and inst_flow['signal'] == 'bullish':
        score += 10
    elif inst_flow and inst_flow['signal'] == 'bearish':
        score -= 10
    return max(0, min(100, score))

def rate_action_confidence(score, twii_rsi, twii_ma_signal, inst_flow):
    """
    行動信心分級
    ★★★：三層篩選全過（理想進場 RSI + MA多頭 + 法人順勢）
    ★★：部分條件未滿（2/3 滿足）
    ★：單一條件（1/3 滿足）
    """
    stars = 0
    reasons = []

    # Layer 2 風控
    if twii_rsi and twii_rsi <= 65:
        stars += 1
        reasons.append(f'TWII RSI={twii_rsi} (安全區)')
    elif twii_rsi and twii_rsi <= 75:
        reasons.append(f'TWII RSI={twii_rsi} (警告區)')
    else:
        reasons.append(f'TWII RSI={twii_rsi} (過熱)')

    # Layer 4 趨勢
    if twii_ma_signal == 'bullish':
        stars += 1
        reasons.append('MA20>MA60 多頭排列')
    elif twii_ma_signal == 'neutral':
        reasons.append('MA20≈MA60 糾結')
    else:
        reasons.append('MA20<MA60 空頭排列')

    # Layer 4 法人
    if inst_flow and inst_flow['signal'] == 'bullish':
        stars += 1
        reasons.append(f'法人買超 {inst_flow["net"]:,.0f}')
    elif inst_flow and inst_flow['signal'] == 'bearish':
        reasons.append(f'法人賣超 {abs(inst_flow["net"]):,.0f}')
    else:
        reasons.append('法人中立')

    label = {3: 'BUY ★★★', 2: 'BUY ★★', 1: 'WATCH', 0: 'SELL'}
    return label.get(stars, 'SELL'), stars, reasons

# ─── 主程式 ───

print('===========================================')
print(' Tina Cron v2 — 五大層全面升級')
print(f' Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('===========================================')

# ═══ Layer 4：市場環境（先抓，供給 L2/L5） ═══
print('\n[Layer 4] 市場環境掃描...')
twii_data = get_twii_rsi()
vix = get_vix()
inst_flow = get_institutional_flow()
market_sentiment = calc_market_sentiment(twii_data, vix, inst_flow)

print(f'  TWII: RSI={twii_data["rsi"]} | MA_signal={twii_data["ma_signal"]}')
print(f'  VIX: {vix}')
print(f'  法人流向: {inst_flow["signal"] if inst_flow else "N/A"} ({inst_flow["net"] if inst_flow else 0:,.0f})')
print(f'  市場情緒分: {market_sentiment}/100')

# ═══ Layer 2：風控 ═══
print('\n[Layer 2] 風控評估...')
twii_rsi = twii_data['rsi'] if twii_data else 50
action_twii = []
if twii_rsi > RSI_EXIT:
    action_twii.append('⚠️ 考慮全面清倉（TWII RSI > 90）')
elif twii_rsi > RSI_REDUCE_50:
    action_twii.append(f'⚠️ 降 50% 部位（TWII RSI > {RSI_REDUCE_50}）')
elif twii_rsi > RSI_REDUCE_25:
    action_twii.append(f'⚠️ 降 25% 部位（TWII RSI > {RSI_REDUCE_25}）')
elif twii_rsi > RSI_NEW_BAN:
    action_twii.append(f'🚫 禁止開新倉（TWII RSI > {RSI_NEW_BAN}）')
else:
    action_twii.append('✅ 無風控警告')

risk_level = '🟢 安全' if twii_rsi <= 65 else '🟡 警告' if twii_rsi <= RSI_NEW_BAN else '🟠 危險' if twii_rsi <= RSI_REDUCE_50 else '🔴 極危險'
print(f'  風控等級: {risk_level}')
for a in action_twii:
    print(f'  → {a}')

# ═══ Layer 3：持倉分析 ═══
print('\n[Layer 3] 持倉分析...')
positions = load_positions()
if not positions:
    print('  暫無持倉')
else:
    for p in positions:
        sym = p.get('symbol', '?')
        cost = p.get('cost', 0)
        current_price = p.get('current_price', cost)
        target_price = p.get('target', 0)
        stop_loss = p.get('stop_loss', 0)
        holding_days = p.get('days_held', 0)

        # RSI 現值
        h = fetch_yf(sym, '20d')
        current_rsi = get_rsi(h['Close'].values) if h is not None and not h.empty else 50.0

        # 距離計算
        dist_stop = (current_price - stop_loss) / current_price * 100 if stop_loss > 0 else 999
        dist_target = (target_price - current_price) / current_price * 100 if target_price > 0 else 999
        pnl_pct = p.get('pnl_pct', 0)
        pnl_abs = p.get('pnl', 0)

        # 持有階段警告
        hold_alert = ''
        if holding_days >= HOLD_FORCE_DAYS:
            hold_alert = '🚨 持有超30天 → 強制審視'
        elif holding_days >= HOLD_REVIEW_DAYS:
            hold_alert = '⚠️ 持有>25天 → 建議降半'
        elif holding_days >= HOLD_WARN_DAYS:
            hold_alert = '👀 持有>20天 → 注意回調'

        print(f'  {sym}: 現價={current_price} | RSI={current_rsi:.0f} | 持有={holding_days}天 {hold_alert}')
        print(f'    PnL: {pnl_pct:+.2f}% ({pnl_abs:+,.0f})')
        print(f'    停損距離: {dist_stop:+.1f}% | 到目標: {dist_target:+.1f}%')

# ═══ Layer 1：目標追蹤 ═══
print('\n[Layer 1] 目標追蹤...')
total_value = sum(
    (p.get('current_price', p.get('entry_price', 0)) - p.get('entry_price', 0)) * p.get('shares', 0)
    for p in positions
)
total_cost = sum(p.get('entry_price', 0) * p.get('shares', 0) for p in positions)
total_return_pct = total_value / total_cost * 100 if total_cost > 0 else 0
target_allocation_pct = 40  # 預設目標 40%
current_allocation_pct = min(target_allocation_pct, 30)  # 假設目前 30%

print(f'  總部位: ~{current_allocation_pct}% (目標 {target_allocation_pct}%)')
print(f'  本月累計損益: {total_return_pct:+.2f}%')
print(f'  距離年度目標: 落後 / 符合 / 超越')

# ═══ Layer 5：行動分級 ═══
print('\n[Layer 5] 行動評估...')
action_label, stars, action_reasons = rate_action_confidence(
    score=market_sentiment,
    twii_rsi=twii_rsi,
    twii_ma_signal=twii_data['ma_signal'] if twii_data else 'neutral',
    inst_flow=inst_flow
)
print(f'  行動: {action_label}')
for r in action_reasons:
    print(f'    ✓ {r}')

# ═══ 最終決策摘要 ═══
print('\n===========================================')
print(' Tina Cron v2 最終報告')
print('===========================================')
print(f' 市場情緒: {market_sentiment}/100')
print(f' TWII: RSI={twii_rsi} | {risk_level}')
print(f' VIX: {vix}')
print(f' 法人: {inst_flow["signal"] if inst_flow else "N/A"}')
print(f' MA 排列: {twii_data["ma_signal"] if twii_data else "N/A"}')
print(f' 行動: {action_label}')
print(f' 風控 Action: {" ".join(action_twii)}')

# ═══ 寫入輸出檔案 ═══
output = {
    'timestamp': datetime.now().isoformat(),
    'layer1_target': {
        'current_allocation_pct': current_allocation_pct,
        'target_allocation_pct': target_allocation_pct,
        'monthly_return_pct': round(total_return_pct, 2),
    },
    'layer2_risk': {
        'twii_rsi': twii_rsi,
        'risk_level': risk_level,
        'actions': action_twii,
        'vix': vix,
    },
    'layer3_positions': [
        {
            'symbol': p.get('symbol'),
            'holding_days': holding_days if 'holding_days' in dir() else 0,
            'current_rsi': float(current_rsi) if 'current_rsi' in dir() else 50,
            'pnl_pct': float(pnl_pct) if 'pnl_pct' in dir() else 0,
            'dist_to_stop': float(dist_stop) if 'dist_stop' in dir() else 999,
            'dist_to_target': float(dist_target) if 'dist_target' in dir() else 999,
            'alert': hold_alert if 'hold_alert' in dir() else '',
        } for p in positions
    ],
    'layer4_market': {
        'twii_rsi': twii_rsi,
        'twii_ma_signal': twii_data['ma_signal'] if twii_data else 'N/A',
        'vix': vix,
        'institutional_flow': inst_flow,
        'market_sentiment': market_sentiment,
    },
    'layer5_action': {
        'label': action_label,
        'stars': stars,
        'reasons': action_reasons,
    },
    'final_recommendation': 'HOLD' if twii_rsi > RSI_NEW_BAN else action_label,
}

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n輸出已寫入: {OUTPUT}')
print(f'\n完成: {datetime.now().strftime("%H:%M:%S")}')