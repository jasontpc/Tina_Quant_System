"""
Tina 自主學習出场機制 — Exit Decision Engine v2.0
stores/portfolio/exit_engine.py

v2.0 重大更新：
- 雙軌制：快速觸發（第1層）優先於綜合評分（第2層）
- 時間紀律：持有 > 15天強制減碼，> 20天全數離場
- 閾值與 SOP_PAPER_TRADE v2.0 完全對齊

自主學習邏輯：
- 每筆交易記錄進/出场的技術條件
- 記錄實際結果 vs 預期
- 統計勝率高的出场條件組合
- 定期更新權重
"""

import json
import os
from datetime import datetime

# ============================================================
# 閾值（與 SOP_PAPER_TRADE v2.0 完全對齊）
# ============================================================
THRESHOLDS = {
    # Fast Trigger P0 — 立即行動
    'hard_stop_loss':   -8.0,   # 虧損 ≤ -8% → EXIT_NOW
    'take_profit':      10.0,   # 盈利 ≥ +10% → EXIT_HALF
    # Fast Trigger P1
    'rsi_danger':       75,     # RSI > 75 → EXIT_HALF
    'twii_systemic':    85,     # TWII RSI > 85 → 全系統減碼 50%
    # 移動停利參考
    'rsi_watch':        70,     # RSI > 70 → 觀察
    'rsi_overheat':     65,     # RSI > 65 → 注意
    # 技術信號
    'kdj_overbought_j':  90,     # J > 90 高檔
    'twii_overheat':    82,     # TWII RSI > 82 系統減碼
    # 軟性止損
    'soft_stop_loss':   -5.0,   # 虧損 > -5% 預警
}

# ============================================================
# 評分維度權重（0-100 總分制）
# ============================================================
DIMENSION_WEIGHTS = {
    'rsi':          25,   # RSI 過熱程度
    'kdj':          15,   # KDJ 高檔/死叉
    'macd':         15,   # MACD 空方
    'price_action': 20,   # 價格破線
    'market':       15,   # 市場系統風險
    'pnl':          10,   # 盈虧紀律
}

# ============================================================
# 評分門檻（與 v2.0 SOP 對齊）
# ============================================================
SCORE_THRESHOLDS = {
    'EXIT_NOW':    90,   # 立即全數離場
    'EXIT_HALF':   70,   # 賣出一半
    'WATCH':       50,   # 密切關注
    'HOLD':         0,   # 正常持有
}

# ============================================================
# 時間紀律門檻（與 v2.0 SOP 對齊）
# ============================================================
TIME_LIMITS = {
    'move_stop':     10,   # 持有 > 10天 → 移動停利至 MA5
    'force_reduce': 15,   # 持有 > 15天 → 強制減碼 50%
    'force_exit':   20,   # 持有 > 20天 → 全數離場（除非 RSI < 40）
}

# ============================================================
# 學習記錄存儲
# ============================================================
LEDGER_PATH = os.path.join(os.path.dirname(__file__), 'exit_decisions.json')

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'decisions': [], 'patterns': {}, 'stats': {}}

def save_ledger(data):
    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 核心評分函數（雙軌制）
# ============================================================
def score_exit(symbol, position_data, market_data=None):
    """
    計算出场分數 0-100，分數越高越應該出场
    採用【雙軌制】：
      第1層：快速觸發（優先於評分，符合即時行動）
      第2層：綜合評分（常規決策）
    """
    lc = position_data['last_check']
    rsi        = lc.get('rsi', 50)
    macd_hist  = lc.get('macd_hist', 0)
    price      = lc.get('price', 0)
    ma5        = lc.get('ma5', 0)
    ma20       = lc.get('ma20', 0)
    pnl        = lc.get('pnl_pct', 0)
    k_val      = lc.get('kdj_K', 50)
    j_val      = lc.get('kdj_J', 50)
    d_val      = lc.get('kdj_D', 50)

    twii_rsi   = market_data.get('twii_rsi', 50) if market_data else 50
    hold_days  = position_data.get('hold_days', 0)

    # ─────────────────────────────────────────────
    # 第1層：快速觸發（命中即時行動，不看分數）
    # ─────────────────────────────────────────────

    # P0：硬止損
    if pnl <= THRESHOLDS['hard_stop_loss']:
        return _fast_trigger(symbol, 'EXIT_NOW', 100,
                             f'HardStopLoss: {pnl:+.1f}% <= -8%',
                             'P0_HARD_STOP_LOSS')

    # P0：到達目標價
    if pnl >= THRESHOLDS['take_profit']:
        return _fast_trigger(symbol, 'EXIT_HALF', 95,
                             f'TakeProfit: {pnl:+.1f}% >= +10%',
                             'P0_TAKE_PROFIT')

    # P1：RSI 過熱
    if rsi > THRESHOLDS['rsi_danger']:
        return _fast_trigger(symbol, 'EXIT_HALF', 85,
                             f'RSIdanger: {rsi:.0f} > 75',
                             'P1_RSI_DANGER')

    # P1：跌破 MA20（無論盈虧）
    if ma20 > 0 and price < ma20:
        return _fast_trigger(symbol, 'EXIT_HALF', 88,
                             f'BelowMA20: {price:.1f} < {ma20:.1f}',
                             'P1_BELOW_MA20')

    # ─────────────────────────────────────────────
    # 時間紀律（持有超期強制減碼）
    # ─────────────────────────────────────────────
    if hold_days > TIME_LIMITS['force_exit']:
        # 持有 > 20天：全數離場（RSI < 40 特殊豁免）
        if rsi < 40:
            # RSI 低檔，給予豁免但只持有
            signal = 'HOLD'
            total = 10
            signals = [f'HoldDays>20豁免: RSI={rsi:.0f}<40']
            fast = False
        else:
            return _fast_trigger(symbol, 'EXIT_NOW', 100,
                                f'HoldDays>20: {hold_days}天，RSI={rsi:.0f}，強制離場',
                                'P0_TIME_HARD_LIMIT')
    elif hold_days > TIME_LIMITS['force_reduce']:
        # 持有 > 15天：強制減碼 50%
        return _fast_trigger(symbol, 'EXIT_HALF', 75,
                             f'HoldDays>15: {hold_days}天，強制減碼50%',
                             'P1_TIME_LIMIT')

    # ─────────────────────────────────────────────
    # 第2層：綜合評分
    # ─────────────────────────────────────────────
    signals = []
    details = {}

    # 1. RSI 評分 (max 25)
    rsi_score = 0
    if rsi > THRESHOLDS['rsi_danger']:       # > 75
        rsi_score = 25
        signals.append(f'RSIdanger:{rsi:.0f}>75')
    elif rsi > THRESHOLDS['rsi_watch']:      # > 70
        rsi_score = 18
        signals.append(f'RSIwatch:{rsi:.0f}>70')
    elif rsi > THRESHOLDS['rsi_overheat']:  # > 65
        rsi_score = 8
        signals.append(f'RSIheat:{rsi:.0f}>65')
    details['rsi_score'] = rsi_score

    # 2. KDJ 評分 (max 15)
    kdj_score = 0
    if j_val > THRESHOLDS['kdj_overbought_j']:
        kdj_score = 10
        signals.append(f'Jhigh:{j_val:.0f}>90')
    if k_val < d_val:  # 死叉
        kdj_score += 5
        signals.append('K<D死叉')
    details['kdj_score'] = kdj_score

    # 3. MACD 評分 (max 15)
    macd_score = 0
    if macd_hist < 0:
        macd_score = 15
        signals.append(f'MACDneg:{macd_hist:+.2f}')
    details['macd_score'] = macd_score

    # 4. 價格破線 (max 20)
    pa_score = 0
    if ma5 > 0 and price < ma5:
        pa_score += 8
        signals.append(f'belowMA5:{price:.1f}<{ma5:.1f}')
    if ma20 > 0 and price < ma20:
        pa_score += 12
        signals.append(f'belowMA20:{price:.1f}<{ma20:.1f}')
    details['price_action_score'] = pa_score

    # 5. 市場系統風險 (max 15)
    mkt_score = 0
    if twii_rsi > THRESHOLDS['twii_overheat']:
        mkt_score = 15
        signals.append(f'TWIIheat:{twii_rsi:.0f}>82')
    elif twii_rsi > 78:
        mkt_score = 8
        signals.append(f'TWIIcaution:{twii_rsi:.0f}>78')
    details['market_score'] = mkt_score

    # 6. 盈虧紀律 (max 10)
    pnl_score = 0
    if pnl >= THRESHOLDS['take_profit']:        # ≥ +10%
        pnl_score = 10
        signals.append(f'TakeProfit:{pnl:+.1f}%>=+10%')
    elif pnl <= THRESHOLDS['hard_stop_loss']:   # ≤ -8%
        pnl_score = 10
        signals.append(f'HardStop:{pnl:+.1f}%<=-8%')
    elif pnl <= THRESHOLDS['soft_stop_loss']:   # ≤ -5%
        pnl_score = 5
        signals.append(f'SoftStop:{pnl:+.1f}%<=-5%')
    details['pnl_score'] = pnl_score

    total = rsi_score + kdj_score + macd_score + pa_score + mkt_score + pnl_score

    # 信號轉換
    if total >= SCORE_THRESHOLDS['EXIT_NOW']:
        signal = 'EXIT_NOW'
    elif total >= SCORE_THRESHOLDS['EXIT_HALF']:
        signal = 'EXIT_HALF'
    elif total >= SCORE_THRESHOLDS['WATCH']:
        signal = 'WATCH'
    else:
        signal = 'HOLD'

    return {
        'symbol': symbol,
        'total_score': total,
        'signal': signal,
        'signals': signals,
        'breakdown': details,
        'fast_trigger': False,
        'timestamp': datetime.now().isoformat(),
    }


def _fast_trigger(symbol, signal, score, reason, fast_type):
    """快速觸發工廠函數"""
    return {
        'symbol': symbol,
        'total_score': score,
        'signal': signal,
        'signals': [reason],
        'breakdown': {'fast_trigger': fast_type},
        'fast_trigger': True,
        'timestamp': datetime.now().isoformat(),
    }


# ============================================================
# 自主學習 — 記錄結果並更新 pattern
# ============================================================
def record_decision(position_data, decision, actual_result=None):
    """
    記錄一次出场決策，用於學習
    actual_result: 'profit' | 'loss' | 'breakeven' — 結果事後更新
    """
    ledger = load_ledger()
    entry = {
        'symbol': position_data['symbol'],
        'date': datetime.now().strftime('%Y-%m-%d'),
        'decision': decision,
        'price_at_decision': position_data['last_check']['price'],
        'cost': position_data['cost'],
        'pnl_at_decision': position_data['last_check']['pnl_pct'],
        'technicals': {
            'rsi': position_data['last_check'].get('rsi'),
            'macd_hist': position_data['last_check'].get('macd_hist'),
            'kdj_J': position_data['last_check'].get('kdj_J'),
        },
        'actual_result': actual_result,
    }
    ledger['decisions'].append(entry)

    if actual_result:
        pattern_key = f"{decision}_{actual_result}"
        ledger['patterns'][pattern_key] = ledger['patterns'].get(pattern_key, 0) + 1

    total = len(ledger['decisions'])
    profitable = sum(1 for d in ledger['decisions'] if d['actual_result'] == 'profit')
    ledger['stats'] = {
        'total_decisions': total,
        'profitable': profitable,
        'win_rate': profitable / total if total > 0 else 0,
    }

    save_ledger(ledger)
    return ledger['stats']


def get_learned_insights():
    """從歷史決策中提取洞察"""
    ledger = load_ledger()
    insights = []
    stats = ledger.get('stats', {})

    if stats.get('win_rate', 0) > 0:
        insights.append(f"歷史勝率: {stats['win_rate']*100:.0f}% ({stats['profitable']}贏/{stats['total_decisions']}筆)")

    patterns = ledger.get('patterns', {})
    for key, count in sorted(patterns.items(), key=lambda x: -x[1]):
        insights.append(f"  {key}: {count}次")

    return insights


# ============================================================
# 批量評分 — 供 daily_review 調用
# ============================================================
def score_all_positions(positions_data, market_data=None):
    results = []
    for pos in positions_data.get('positions', []):
        r = score_exit(pos['symbol'], pos, market_data)
        results.append(r)
    return sorted(results, key=lambda x: -x['total_score'])


# ============================================================
# 訊號文字對照（v2.0）
# ============================================================
SIGNAL_TEXT = {
    'EXIT_NOW':  '🔴 立即出场',
    'EXIT_HALF': '🟠 出场一半',
    'WATCH':     '🟡 密切关注',
    'HOLD':      '🟢 正常持有',
}


def format_exit_report(scored_positions):
    """格式化評分報告，包含快速觸發標記"""
    lines = []
    lines.append("=" * 55)
    lines.append("  自主学习出场机制 v2.0 — 评分报告")
    lines.append("=" * 55)

    for r in scored_positions:
        signal_text = SIGNAL_TEXT.get(r['signal'], r['signal'])
        fast_tag = " ⚡快速觸發" if r.get('fast_trigger', False) else ""
        lines.append(f"\n[{r['symbol']}] {signal_text}{fast_tag}")
        lines.append(f"  分数: {r['total_score']}/100")
        lines.append(f"  触发: {', '.join(r['signals']) if r['signals'] else '无'}")
        bd = r['breakdown']
        if 'fast_trigger' not in bd:
            lines.append(f"  明细: RSI {bd.get('rsi_score',0)} | KDJ {bd.get('kdj_score',0)} | MACD {bd.get('macd_score',0)} | PA {bd.get('price_action_score',0)} | MKT {bd.get('market_score',0)} | PnL {bd.get('pnl_score',0)}")

    lines.append("\n" + "=" * 55)
    insights = get_learned_insights()
    if insights:
        lines.append("  学习洞察:")
        for i in insights:
            lines.append(f"    {i}")
    lines.append("=" * 55)
    return "\n".join(lines)


if __name__ == '__main__':
    # 測試
    positions = {
        'positions': [
            {'symbol': '3034.TW', 'name': '緯穎', 'cost': 442, 'shares': 671, 'hold_days': 5,
             'last_check': {'price': 487.5, 'rsi': 71.8, 'macd_hist': 8.06, 'kdj_J': 105, 'kdj_K': 84, 'kdj_D': 74, 'ma5': 441.5, 'ma20': 398.5, 'pnl_pct': 10.3}},
            {'symbol': '2376.TW', 'name': '技嘉', 'cost': 301, 'shares': 664, 'hold_days': 5,
             'last_check': {'price': 319.5, 'rsi': 66.7, 'macd_hist': 3.34, 'kdj_J': 94, 'kdj_K': 77, 'kdj_D': 69, 'ma5': 301.0, 'ma20': 263.5, 'pnl_pct': 6.1}},
            {'symbol': '2379.TW', 'name': '環球晶', 'cost': 543, 'shares': 367, 'hold_days': 5,
             'last_check': {'price': 563.0, 'rsi': 53.0, 'macd_hist': 1.28, 'kdj_J': 60, 'kdj_K': 54, 'kdj_D': 50, 'ma5': 544.0, 'ma20': 524.0, 'pnl_pct': 3.7}},
            # 測試時間紀律：持有 > 15天
            {'symbol': '9999.TW', 'name': '測試股', 'cost': 100, 'shares': 100, 'hold_days': 16,
             'last_check': {'price': 105, 'rsi': 55, 'macd_hist': 0.5, 'kdj_J': 55, 'kdj_K': 55, 'kdj_D': 55, 'ma5': 104, 'ma20': 103, 'pnl_pct': 5.0}},
        ]
    }
    market = {'twii_rsi': 82.5}
    results = score_all_positions(positions, market)
    print(format_exit_report(results))