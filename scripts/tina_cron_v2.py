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
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ─── VRAM 守護 ───────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))
try:
    from ray_guard import ray_singleton
except ImportError:
    # 如果 ray_guard 不存在，定義一個空裝飾器
    def ray_singleton(func): return func

# ─── 路徑設定 ───
BASE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(BASE, 'data')
POSITIONS_FILE = os.path.join(DATA_DIR, 'position_tracker.json')
DB = os.path.join(DATA_DIR, 'master_backtest.db')
WISDOM_DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
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

def get_us_macro():
    """L4 美股宏觀：NDX/SPX/TNX/WTI/DXY"""
    result = {}
    try:
        spx = yf.Ticker('^GSPC').history(period='60d')
        if not spx.empty:
            c = spx['Close'].values
            delta = np.diff(c)
            g = np.where(delta > 0, delta, 0)
            l = np.where(delta < 0, -delta, 0)
            ag = np.mean(g[-14:])
            al = np.mean(l[-14:])
            spx_rsi = 100 - (100 / (1 + ag / al)) if al != 0 else 50
            result['SPX'] = round(float(spx['Close'].values[-1]), 2)
            result['SPX_RSI'] = round(float(spx_rsi), 1)
    except:
        pass
    try:
        ndx = yf.Ticker('^IXIC').history(period='10d')
        if not ndx.empty:
            result['NDX'] = round(float(ndx['Close'].values[-1]), 2)
    except:
        pass
    try:
        tnx = yf.Ticker('^TNX').history(period='10d')
        if not tnx.empty:
            result['TNX'] = round(float(tnx['Close'].values[-1]), 3)
    except:
        pass
    try:
        wti = yf.Ticker('CL=F').history(period='10d')
        if not wti.empty:
            result['WTI'] = round(float(wti['Close'].values[-1]), 2)
    except:
        pass
    try:
        dxy = yf.Ticker('DXY').history(period='10d')
        if not dxy.empty:
            result['DXY'] = round(float(dxy['Close'].values[-1]), 2)
    except:
        pass
    return result

def calc_risk_zone(twii_rsi, vix, wti, pos_rsis):
    """L2 多因子 Red Zone 判定（對齊 Ray 風險門檻系統）"""
    factors = {
        'TWII_RSI': twii_rsi <= 90,
        'VIX': vix is not None and vix < 25,
        'WTI': wti is not None and wti < 100,
        'STOCK_RSI': all(r < 80 for r in pos_rsis if r)
    }
    green = sum(1 for v in factors.values() if v)
    red_count = sum(1 for v in factors.values() if not v)
    if red_count >= 2:
        return '🔴 RED', factors, f'{red_count}因子達Red Zone'
    elif red_count == 1:
        return '🟡 YELLOW', factors, f'{red_count}因子警告'
    else:
        return '🟢 GREEN', factors, '全因子正常'

def get_forbidden_rules():
    """L3 讀取 Ray 禁止規則"""
    try:
        conn = sqlite3.connect(WISDOM_DB)
        c = conn.cursor()
        c.execute("SELECT diagnosis FROM wisdom_corrections WHERE diagnosis LIKE 'If%' LIMIT 5")
        rules = [r[0] for r in c.fetchall()]
        conn.close()
        return rules
    except:
        return []

def check_forbidden_violation(forbidden_rules, twii_rsi, vix, pos_rsi, holding_days):
    """L3 檢查是否觸發禁止規則，返回 True=需止損"""
    if not forbidden_rules:
        return False, ''
    # 簡化判斷：根據 RSI 和天數推斷是否接近禁止條件
    if pos_rsi and pos_rsi > 80 and holding_days > 7:
        return True, f'RSI={pos_rsi:.0f}>80 且持有{holding_days}天>7'
    return False, ''

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

def rate_action_confidence(score, twii_rsi, twii_ma_signal, inst_flow, wisdom_db=None):
    """
    行動信心分級
    ★★★：四層篩選全過（理想進場 RSI + MA多頭 + 法人順勢 + Wisdom 驗證）
    ★★：部分條件未滿（3/4 滿足）
    ★：單一條件（2/4 滿足）
    """
    stars = 0
    reasons = []

    # ── Layer 2: 風控 ──
    if twii_rsi and twii_rsi <= 65:
        stars += 1
        reasons.append(f'TWII RSI={twii_rsi} (安全區)')
    elif twii_rsi and twii_rsi <= 75:
        reasons.append(f'TWII RSI={twii_rsi} (警告區)')
    else:
        reasons.append(f'TWII RSI={twii_rsi} (過熱)')

    # ── Layer 4: 趨勢 ──
    if twii_ma_signal == 'bullish':
        stars += 1
        reasons.append('MA20>MA60 多頭排列')
    elif twii_ma_signal == 'neutral':
        reasons.append('MA20=MA60 糾結')
    else:
        reasons.append('MA20<MA60 空頭排列')

    # ── Layer 4: 法人 ──
    if inst_flow and inst_flow['signal'] == 'bullish':
        stars += 1
        reasons.append(f'法人買超 {inst_flow["net"]:,.0f}')
    elif inst_flow and inst_flow['signal'] == 'bearish':
        reasons.append(f'法人賣超 {abs(inst_flow["net"]):,.0f}')
    else:
        reasons.append('法人中立')

    # ── Layer 5: Wisdom 驗證（新增）───
    if wisdom_db:
        try:
            import sqlite3
            conn = sqlite3.connect(wisdom_db)
            c = conn.cursor()
            # 讀取高信心教訓數量
            c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.75')
            solid = c.fetchone()[0]
            # 讀取 web 教訓數量
            c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE meta_label='qwen2.5:7b' OR meta_label='ray-deep-v1'")
            deep = c.fetchone()[0]
            conn.close()

            wisdom_score = (solid / 67.0 * 2) + (deep / 67.0 * 1)  # 加權
            if wisdom_score >= 0.8:
                stars += 1
                reasons.append(f'Wisdom 充足 ({solid} 高信心 + {deep} 深度)')
            elif wisdom_score >= 0.4:
                reasons.append(f'Wisdom 累積中 ({solid}+{deep} rows)')
            else:
                reasons.append(f'Wisdom 不足 ({solid}+{deep}) — 謹慎行動')
        except Exception as e:
            reasons.append(f'Wisdom讀取失敗: {e}')
    else:
        reasons.append('Wisdom DB 未接入')

    label = {4: 'BUY ★★★', 3: 'BUY ★★', 2: 'WATCH', 1: 'WATCH', 0: 'SELL'}
    return label.get(stars, 'SELL'), stars, reasons

# ─── 主程式 ───

# ══ VRAM 守護：確保本腳本執行時佔用獨占鎖 ══
@ray_singleton
def run_tina_cron_v2():
    print('===========================================')
    print(' Tina Cron v2 — 五大層全面升級')
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('===========================================')

    # ═══ Layer 4：市場環境（先抓，供給 L2/L5） ═══
    print('\n[Layer 4] 市場環境掃描...')
    twii_data = get_twii_rsi()
    vix = get_vix()
    us_macro = get_us_macro()  # L4 美股宏觀
    inst_flow = get_institutional_flow()
    market_sentiment = calc_market_sentiment(twii_data, vix, inst_flow)

    # positions 提早在 L2 之前讀取（L2/L3 都用到）
    positions = load_positions()

print(f'  TWII: RSI={twii_data["rsi"]} | MA_signal={twii_data["ma_signal"]}')
print(f'  VIX: {vix}')
print(f'  US Macro: SPX={us_macro.get("SPX")} RSI={us_macro.get("SPX_RSI")} NDX={us_macro.get("NDX")} TNX={us_macro.get("TNX")} WTI={us_macro.get("WTI")}')
print(f'  法人流向: {inst_flow["signal"] if inst_flow else "N/A"} ({inst_flow["net"] if inst_flow else 0:,.0f})')
print(f'  市場情緒分: {market_sentiment}/100')
print(f'  持倉: {len(positions)} 檔')

# ═══ Layer 2：風控（多因子 Red Zone） ═══
print('\n[Layer 2] 風控評估...')
twii_rsi = twii_data['rsi'] if twii_data else 50
wti_val = us_macro.get('WTI', None)
pos_rsis = []
for p in positions:
    sym = p.get('symbol', '?')
    h = fetch_yf(sym, '20d')
    if h is None or h.empty:
        h2 = fetch_yf(sym + '.TW', '20d')
        if h2 is not None and not h2.empty:
            h = h2
    if h is not None and not h.empty:
        pos_rsis.append(get_rsi(h['Close'].values))

zone_icon, zone_factors, zone_desc = calc_risk_zone(twii_rsi, vix, wti_val, pos_rsis)
print(f'  風險區域: {zone_icon} {zone_desc}')
for k, v in zone_factors.items():
    icon = '✅' if v else '❌'
    print(f'    {icon} {k}: {"OK" if v else "RED"}')

action_twii = []
if zone_icon == '🔴 RED':
    action_twii.append('🔴 多因子 RED ZONE → 禁止加倉，檢視所有持倉')
elif zone_icon == '🟡 YELLOW':
    action_twii.append('🟡 YELLOW ZONE → 謹慎操作，觀望')
else:
    if twii_rsi > RSI_EXIT:
        action_twii.append('⚠️ TWII RSI>90 → 考慮全面清倉')
    elif twii_rsi > RSI_REDUCE_50:
        action_twii.append(f'⚠️ TWII RSI>{RSI_REDUCE_50} → 降50%部位')
    elif twii_rsi > RSI_REDUCE_25:
        action_twii.append(f'⚠️ TWII RSI>{RSI_REDUCE_25} → 降25%部位')
    elif twii_rsi > RSI_NEW_BAN:
        action_twii.append(f'🚫 TWII RSI>{RSI_NEW_BAN} → 禁新倉')
    else:
        action_twii.append('✅ 無風控警告')

risk_level = zone_icon
for a in action_twii:
    print(f'  → {a}')

# ═══ Layer 3：持倉分析 ═══
print('\n[Layer 3] 持倉分析...（含禁止規則檢查）')
forbidden_rules = get_forbidden_rules()  # L3 Ray 禁止規則
print(f'  讀取 {len(forbidden_rules)} 條禁止規則')
layer3_positions = []
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
        if h is None or h.empty:
            h = fetch_yf(sym + '.TW', '20d')
        current_rsi = get_rsi(h['Close'].values) if h is not None and not h.empty else 50.0

        # 距離計算
        dist_stop = (current_price - stop_loss) / current_price * 100 if stop_loss > 0 else 999
        dist_target = (target_price - current_price) / current_price * 100 if target_price > 0 else 999
        pnl_pct = p.get('pnl_pct', 0)
        pnl_abs = p.get('pnl', 0)

        # L3 禁止規則檢查
        violate, reason = check_forbidden_violation(forbidden_rules, twii_rsi, vix, current_rsi, holding_days)

        # 持有階段警告
        hold_alert = ''
        if holding_days >= HOLD_FORCE_DAYS:
            hold_alert = '🚨 持有超30天 → 強制審視'
        elif holding_days >= HOLD_REVIEW_DAYS:
            hold_alert = '⚠️ 持有>25天 → 建議降半'
        elif holding_days >= HOLD_WARN_DAYS:
            hold_alert = '👀 持有>20天 → 注意回調'

        alert_icon = '🛑' if violate else '  '
        print(f'  {alert_icon}{sym}: 現價={current_price} | RSI={current_rsi:.0f} | 持有={holding_days}天 {hold_alert}')
        if violate:
            print(f'     🛑 禁止規則觸發: {reason}')
        print(f'    PnL: {pnl_pct:+.2f}% ({pnl_abs:+,.0f})')
        print(f'    停損距離: {dist_stop:+.1f}% | 到目標: {dist_target:+.1f}%')

        # 收集 layer3_positions（避免 comprehension 閉包問題）
        layer3_positions.append({
            'symbol': sym,
            'holding_days': holding_days,
            'current_rsi': float(current_rsi),
            'pnl_pct': float(pnl_pct),
            'dist_to_stop': float(dist_stop),
            'dist_to_target': float(dist_target),
            'alert': hold_alert,
            'forbidden_violation': reason if violate else '',
        })

# ═══ Layer 1：目標追蹤（掛鉤 backtest_reports 實質成果） ═══
print('\n[Layer 1] 目標追蹤...')

# 從 backtest_reports 取得實質策略品質
try:
    conn_bt = sqlite3.connect(WISDOM_DB)
    c_bt = conn_bt.cursor()
    c_bt.execute('SELECT AVG(sharpe_ratio), MAX(max_drawdown) FROM backtest_reports WHERE sharpe_ratio > 0')
    bt_row = c_bt.fetchone()
    avg_sharpe = bt_row[0] or 0
    max_mdd = bt_row[1] or 0
    conn_bt.close()
    quality_label = '✅ 穩健' if avg_sharpe >= 1.5 and max_mdd < 15 else '⚠️ 待強化' if avg_sharpe >= 1.0 else '🔴 需改善'
    print(f'  策略品質: Sharpe={avg_sharpe:.2f} MaxDD={max_mdd:.1f}% {quality_label}')
except Exception as e:
    avg_sharpe, max_mdd = 0, 0
    print(f'  策略品質: 無法讀取 ({e})')

total_value = sum(
    (p.get('current_price', p.get('entry_price', 0)) - p.get('entry_price', 0)) * p.get('shares', 0)
    for p in positions
)
total_cost = sum(p.get('entry_price', 0) * p.get('shares', 0) for p in positions)
total_return_pct = total_value / total_cost * 100 if total_cost > 0 else 0
target_allocation_pct = 40
current_allocation_pct = min(target_allocation_pct, 30)

print(f'  總部位: ~{current_allocation_pct}% (目標 {target_allocation_pct}%)')
print(f'  本月累計損益: {total_return_pct:+.2f}%')
print(f'  Sharpe {avg_sharpe:.2f} → 預估月均: {avg_sharpe/12*100:.1f}%（供參考）')
print(f'  距離年度目標: {"領先" if total_return_pct > avg_sharpe/12*100 else "符合" if total_return_pct > 0 else "落後"}')

# ═══ Layer 5：行動分級 ═══
print('\n[Layer 5] 行動評估...')
WISDOM_DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'

action_label, stars, action_reasons = rate_action_confidence(
    score=market_sentiment,
    twii_rsi=twii_rsi,
    twii_ma_signal=twii_data['ma_signal'] if twii_data else 'neutral',
    inst_flow=inst_flow,
    wisdom_db=WISDOM_DB
)
print(f'  行動: {action_label} (Wisdom 已接入)')
for r in action_reasons:
    print(f'    - {r}')

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
        'us_macro': {
            'SPX': us_macro.get('SPX'),
            'SPX_RSI': us_macro.get('SPX_RSI'),
            'NDX': us_macro.get('NDX'),
            'TNX': us_macro.get('TNX'),
            'WTI': us_macro.get('WTI'),
        },
        'zone_factors': zone_factors,
        'zone_desc': zone_desc,
    },
    'layer3_positions': layer3_positions,
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

# ─── 入口 ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    run_tina_cron_v2()
