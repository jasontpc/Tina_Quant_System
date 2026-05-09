# -*- coding: utf-8 -*-
"""
Decision Committee Vote Module v1.0
======================================
表決模組 — 5位委員決策委員會

使用方式：
  python decision_committee_vote.py --action "buy" --symbol 2330.TW --strategy swing
  python decision_committee_vote.py --action "sell" --symbol 0050.TW --strategy etf_trend
  python decision_committee_vote.py --action "buy" --symbol 0056.TW --strategy dca
  python decision_committee_vote.py --report

委員會規則：
  - 5位委員：Tina(分析師)、Nana(波段)、Leo(ETF/DCA)、Macro(總經)、Ray(最終決策)
  - 門檻：至少 3/5 委員同意才能執行
  - 提案類型：buy / sell / hold / watch / skip
  - 票數不足 → 自動改為 watch 或 skip
"""

import json, sqlite3, argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict

WORKSPACE    = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
RESULTS_DIR  = WORKSPACE / 'data' / 'backtest_results'
DB_PATH      = WORKSPACE / 'data' / 'yfinance.db'
CONF_PATH    = WORKSPACE / 'configs' / 'unified_strategy_config.json'
BLACKLIST    = {"2615","1590","2382","2317","2303","3008","3231","2408","3443","6446","6669","2597","2379"}

# ═══════════════════════════════════════════════════════════════════════════
# 委員會成員
# ═══════════════════════════════════════════════════════════════════════════

MEMBERS = {
    'Tina': {
        'role':     '分析師 / Analyst',
        'domain':   '台股數據分析、趨勢判讀、系統整合',
        'color':    '#4895ef',
        'weight':   1.0,
    },
    'Nana': {
        'role':     '波段交易員 / Swing Trader',
        'domain':   '個股波段進出场時機、停損紀律',
        'color':    '#f72585',
        'weight':   1.0,
    },
    'Leo': {
        'role':     'ETF/資產配置 / ETF Allocator',
        'domain':   'ETF、定期定額、資產配置',
        'color':    '#06d6a0',
        'weight':   1.0,
    },
    'Macro': {
        'role':     '總經策略師 / Macro Strategist',
        'domain':   '總經趨勢、地緣政治、央行政策',
        'color':    '#ffd60a',
        'weight':   1.0,
    },
    'Ray': {
        'role':     '最終決策 / Final Decision',
        'domain':   '全領域、資金管理、最終裁決',
        'color':    '#adb5bd',
        'weight':   1.5,   # Ray有更大權重（1.5x）
    },
}

VOTE_THRESHOLD = 3   # 至少 3/5 同意
VOTE_OPTIONS   = ['agree', 'disagree', 'abstain']

ACTION_LABELS = {
    'buy':  '買進',
    'sell': '賣出',
    'hold': '持有',
    'watch':'觀察',
    'skip': '跳過',
}


# ═══════════════════════════════════════════════════════════════════════════
# 數據獲取工具
# ═══════════════════════════════════════════════════════════════════════════

def get_stock_data(symbol: str, days: int = 90) -> Optional[pd.DataFrame]:
    """從本地 DB 取得近期 K 線"""
    conn = sqlite3.connect(str(DB_PATH))
    cutoff = (pd.Timestamp('today') - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    df = pd.read_sql('''
        SELECT date, open, high, low, close, volume,
               rsi_14, atr_14, sma_20, sma_60, sma_120,
               macd_hist, bb_upper, bb_lower, change_pct
        FROM daily_ohlcv
        WHERE symbol=? AND date >= ?
        ORDER BY date
    ''', conn, params=(symbol, cutoff), parse_dates=['date'])
    conn.close()
    if df.empty:
        return None
    df['rsi_14'] = df['rsi_14'].fillna(50)
    df['atr_14']  = df['atr_14'].fillna(df['close'] * 0.02)
    return df


def get_backtest_summary(strategy: str) -> Optional[Dict]:
    """讀取 Phase 4 回測結果（單一策略）"""
    f = RESULTS_DIR / f'backtest_{strategy}_20260509.json'
    if not f.exists():
        return None
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    if not data:
        return None
    rets  = [r['total_return'] for r in data]
    wins  = [r['win_rate'] for r in data]
    dds   = [r['max_drawdown'] for r in data]
    return {
        'n':          len(data),
        'avg_return': np.mean(rets),
        'med_return': np.median(rets),
        'avg_winrate': np.mean(wins),
        'max_dd':     min(dds),
        'best_symbol': max(data, key=lambda x: x['total_return'])['symbol'],
        'best_return': max(r['total_return'] for r in data),
        'worst_symbol': min(data, key=lambda x: x['total_return'])['symbol'],
        'worst_return': min(r['total_return'] for r in data),
    }


def get_latest_price(symbol: str) -> Optional[float]:
    """取得最新收盤價"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT close FROM daily_ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 1', (symbol,))
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else None


def load_config() -> Dict:
    if CONF_PATH.exists():
        with open(CONF_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# ═══════════════════════════════════════════════════════════════════════════
# 分析師評估函式
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_tina(symbol: str, action: str, strategy: str) -> Dict:
    """Tina 分析師觀點"""
    info = {'member': 'Tina', 'vote': 'abstain', 'reason': '', 'confidence': 0, 'tags': []}

    # 黑名單檢查
    sym_clean = symbol.replace('.TW', '').replace('.TWO', '')
    if sym_clean in BLACKLIST:
        info['vote'] = 'disagree'
        info['reason'] = f'{symbol} 在黑名單中'
        info['confidence'] = 10
        info['tags'] = ['blacklist']
        return info

    # 取得基本數據
    df = get_stock_data(symbol, days=90)
    price = get_latest_price(symbol)
    bt = get_backtest_summary(strategy)

    if df is None or df.empty:
        info['reason'] = '無足夠數據'
        return info

    last = df.iloc[-1]
    rsi  = last.get('rsi_14', 50) or 50
    ma20 = last.get('sma_20', 0) or 0
    ma60 = last.get('sma_60', 0) or 0
    atr  = last.get('atr_14', 0) or 0
    mom30 = (last['close'] / df.iloc[-30]['close'] - 1) * 100 if len(df) >= 30 else 0

    # RSI 評估
    if rsi < 30:
        info['tags'].append('RSI超賣')
    elif rsi > 70:
        info['tags'].append('RSI超買')

    # MA 趨勢
    if ma20 > ma60:
        info['tags'].append('MA多頭排列')
    elif ma20 < ma60:
        info['tags'].append('MA空頭排列')

    # 進場評估（基於策略）
    score = 0
    reasons = []

    if strategy in ('swing', 'growth_long'):
        if rsi < 50:
            score += 3; reasons.append(f'RSI={rsi:.1f}<50')
        elif rsi > 65:
            score -= 2; reasons.append(f'RSI={rsi:.1f}>65')
        if ma20 > ma60:
            score += 2; reasons.append('MA多头排列')
        if atr / price < 0.03:
            score += 1; reasons.append('低波動率')

    if bt:
        if bt['avg_return'] > 3:
            score += 1; reasons.append(f"策略歷史報酬+{bt['avg_return']:.1f}%")
        if bt['avg_winrate'] > 60:
            score += 1; reasons.append(f"勝率{bt['avg_winrate']:.0f}%")

    # 投票
    if action == 'buy':
        if score >= 4:
            info['vote'] = 'agree'; info['confidence'] = min(score * 12, 90)
        elif score >= 2:
            info['vote'] = 'agree'; info['confidence'] = min(score * 10, 70)
        else:
            info['vote'] = 'disagree'; info['confidence'] = 60
            reasons.append('綜合評分不足')
    elif action == 'sell':
        if rsi > 70 or mom30 > 20:
            info['vote'] = 'agree'; info['confidence'] = 80
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50

    info['reason'] = '; '.join(reasons) if reasons else f'RSI={rsi:.1f}, MA20={ma20:.0f}, MA60={ma60:.0f}'
    return info


def evaluate_nana(symbol: str, action: str, strategy: str) -> Dict:
    """Nana 波段交易員觀點"""
    info = {'member': 'Nana', 'vote': 'abstain', 'reason': '', 'confidence': 0, 'tags': []}

    sym_clean = symbol.replace('.TW', '').replace('.TWO', '')
    if sym_clean in BLACKLIST:
        info['vote'] = 'disagree'; info['reason'] = f'{symbol} 在黑名單'; info['confidence'] = 10
        return info

    df = get_stock_data(symbol, days=60)
    if df is None or df.empty:
        info['reason'] = '無足夠數據'
        return info

    last  = df.iloc[-1]
    rsi   = last.get('rsi_14', 50) or 50
    atr   = last.get('atr_14', 0) or 0
    price = last.get('close', 0) or 0

    # Nana 的波段規則
    stop_loss   = price * 0.08   # -8%
    target      = price * 0.10   # +10%（波段目標）
    atr_stop    = price - atr * 1.5

    reasons = []

    # 進場時機檢查
    if rsi < 55 and rsi >= 30:
        reasons.append(f'RSI={rsi:.1f}（區間OK）')
    elif rsi < 30:
        reasons.append(f'RSI={rsi:.1f}（超賣，可能反彈）')
    else:
        reasons.append(f'RSI={rsi:.1f}（過高）')

    # ATR 評估波動率
    atr_pct = atr / price * 100
    reasons.append(f'ATR={atr:.1f}（{atr_pct:.1f}%）')

    if atr_pct < 1.5:
        reasons.append('低波動，區間操作')
    elif atr_pct > 4:
        reasons.append('高波動，縮小部位')

    # 停損評估
    if price - atr * 1.5 > stop_loss:
        reasons.append(f'ATR停損${atr_stop:.0f}比%停損${stop_loss:.0f}更合理')
    else:
        reasons.append(f'%停損${stop_loss:.0f}在ATR範圍內')

    if action == 'buy':
        if rsi < 55 and atr_pct > 0.5:
            info['vote'] = 'agree'; info['confidence'] = 75
        elif rsi < 40:
            info['vote'] = 'agree'; info['confidence'] = 80
            reasons.append('極超賣，建議進場')
        else:
            info['vote'] = 'disagree'; info['confidence'] = 60
            reasons.append('RSI不在理想區間')
    elif action == 'sell':
        if rsi > 65:
            info['vote'] = 'agree'; info['confidence'] = 80
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50

    info['reason'] = '; '.join(reasons)
    return info


def evaluate_leo(symbol: str, action: str, strategy: str) -> Dict:
    """Leo ETF/資產配置觀點"""
    info = {'member': 'Leo', 'vote': 'abstain', 'reason': '', 'confidence': 0, 'tags': []}

    df = get_stock_data(symbol, days=120)
    if df is None or df.empty:
        info['reason'] = '無足夠數據'
        return info

    last  = df.iloc[-1]
    rsi   = last.get('rsi_14', 50) or 50
    ma20  = last.get('sma_20', 0) or 0
    ma60  = last.get('sma_60', 0) or 0
    mom60 = (last['close'] / df.iloc[-60]['close'] - 1) * 100 if len(df) >= 60 else 0
    price = last.get('close', 0) or 0

    bt    = get_backtest_summary(strategy if strategy != 'dca' else 'dca')

    reasons = []
    score   = 0

    if strategy == 'dca':
        # DCA 評估
        if rsi < 40:
            score += 4; reasons.append(f'DCA理想進場：RSI={rsi:.1f}<40')
        elif rsi < 50:
            score += 2; reasons.append(f'DCA良好進場：RSI={rsi:.1f}<50')
        if mom60 > 0:
            score += 1; reasons.append(f'60日趨勢+{mom60:.1f}%')
        if bt and bt['avg_return'] > 0:
            score += 1; reasons.append(f'歷史平均+{bt["avg_return"]:.1f}%')

    elif strategy == 'etf_trend':
        # ETF 趨勢評估
        if ma20 > ma60:
            score += 3; reasons.append('MA黃金交叉')
        else:
            score -= 2; reasons.append('MA死亡交叉')
        if rsi < 65:
            score += 1; reasons.append(f'RSI={rsi:.1f}未超買')
        if mom60 > 5:
            score += 2; reasons.append(f'60日動能+{mom60:.1f}%')
        if bt and bt['avg_return'] > 3:
            score += 1; reasons.append(f'策略歷史+{bt["avg_return"]:.1f}%')

    if action == 'buy':
        if score >= 4:
            info['vote'] = 'agree'; info['confidence'] = min(score * 15, 90)
        elif score >= 2:
            info['vote'] = 'agree'; info['confidence'] = 65
        else:
            info['vote'] = 'disagree'; info['confidence'] = 60
            reasons.append('評分不足')
    elif action == 'sell':
        if rsi > 70 or (ma20 < ma60 and strategy == 'etf_trend'):
            info['vote'] = 'agree'; info['confidence'] = 80
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50

    info['reason'] = '; '.join(reasons) if reasons else f'RSI={rsi:.1f}, 60日動能={mom60:.1f}%'
    return info


def evaluate_macro(symbol: str, action: str, strategy: str) -> Dict:
    """Macro 總經策略師觀點"""
    info = {'member': 'Macro', 'vote': 'abstain', 'reason': '', 'confidence': 0, 'tags': []}

    # 嘗試讀取最新宏觀報告
    macro_path = WORKSPACE / 'reports' / 'macro'
    latest_macro = None
    if macro_path.exists():
        files = sorted(macro_path.glob('*.json'), key=lambda x: x.name, reverse=True)
        if files:
            try:
                with open(files[0], 'r', encoding='utf-8') as f:
                    latest_macro = json.load(f)
            except:
                pass

    # 根據 action 類型提供宏觀意見
    reasons = []

    if latest_macro:
        # 嘗試解析總經信號
        try:
            signals = latest_macro.get('signals', {}) or latest_macro.get('data', {})
            tsys = signals.get('Taiwan_System', {})
            usds = signals.get('US_Dollar', {})
            vix  = signals.get('VIX', {})

            if tsys.get('trend') == 'bullish':
                reasons.append('台股系統看漲')
                info['tags'].append('台股多頭')
            elif tsys.get('trend') == 'bearish':
                reasons.append('台股系統看跌')
                info['tags'].append('台股空頭')

            # VIX 評估
            vix_val = vix.get('value', 0) if isinstance(vix, dict) else 0
            if vix_val and float(vix_val) < 15:
                reasons.append(f'VIX={vix_val:.1f}（低波動，風險偏好）')
            elif vix_val and float(vix_val) > 25:
                reasons.append(f'VIX={vix_val:.1f}（高波動，謹慎）')
                info['tags'].append('高波動環境')
        except:
            reasons.append('宏觀數據解析異常')
    else:
        reasons.append('無宏觀數據，默認中性')

    # 根據策略給出方向性判斷
    if action == 'buy':
        # 總經環境是否支持買入
        if any('多頭' in r or '低波動' in r or '風險偏好' in r for r in reasons):
            info['vote'] = 'agree'; info['confidence'] = 70
        elif any('空頭' in r or '高波動' in r for r in reasons):
            info['vote'] = 'disagree'; info['confidence'] = 70
            reasons.append('宏觀環境不利')
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50
    elif action == 'sell':
        if any('空頭' in r or '高波動' in r for r in reasons):
            info['vote'] = 'agree'; info['confidence'] = 75
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50

    info['reason'] = '; '.join(reasons) if reasons else '宏觀中性偏觀望'
    return info


def evaluate_ray(symbol: str, action: str, strategy: str, all_votes: List[Dict]) -> Dict:
    """Ray 最終裁決"""
    info = {'member': 'Ray', 'vote': 'abstain', 'reason': '', 'confidence': 0, 'tags': []}

    # 統計其他委員觀點
    agrees   = sum(1 for v in all_votes if v['vote'] == 'agree')
    disagrees = sum(1 for v in all_votes if v['vote'] == 'disagree')
    abstains = sum(1 for v in all_votes if v['vote'] == 'abstain')

    avg_conf = np.mean([v['confidence'] for v in all_votes]) if all_votes else 50

    reasons = [f'委員分布：{agrees}贊成/{disagrees}反對/{abstains}棄權']

    # Ray 的裁決邏輯
    if action == 'buy':
        if agrees >= 3:
            info['vote'] = 'agree'; info['confidence'] = min(avg_conf + 15, 95)
            reasons.append('多數贊成，確認買入')
        elif agrees == 2 and disagrees <= 1:
            info['vote'] = 'agree'; info['confidence'] = 65
            reasons.append('少數優勢，支持買入')
        elif agrees == 2 and abstains >= 2:
            info['vote'] = 'watch'; info['confidence'] = 60
            reasons.append('共識不足，改為觀察')
        else:
            info['vote'] = 'disagree'; info['confidence'] = max(70, avg_conf)
            reasons.append('多數反對或共識不足')
    elif action == 'sell':
        if disagrees >= 2:
            info['vote'] = 'agree'; info['confidence'] = 75
            reasons.append('多數反對，建議賣出')
        else:
            info['vote'] = 'abstain'; info['confidence'] = 50

    info['reason'] = ' | '.join(reasons)
    return info


# ═══════════════════════════════════════════════════════════════════════════
# 表決引擎
# ═══════════════════════════════════════════════════════════════════════════

def collect_votes(symbol: str, action: str, strategy: str) -> List[Dict]:
    """收集所有委員投票"""
    votes = [
        evaluate_tina(symbol, action, strategy),
        evaluate_nana(symbol, action, strategy),
        evaluate_leo(symbol, action, strategy),
        evaluate_macro(symbol, action, strategy),
    ]
    votes.append(evaluate_ray(symbol, action, strategy, votes[:-1]))
    return votes


def tally_votes(votes: List[Dict]) -> Dict:
    """統計票數，判斷是否通過門檻"""
    agrees    = [v for v in votes if v['vote'] == 'agree']
    disagrees = [v for v in votes if v['vote'] == 'disagree']
    abstains = [v for v in votes if v['vote'] == 'abstain']
    watches  = [v for v in votes if v['vote'] == 'watch']

    agree_count  = len(agrees)
    total_weight = sum(MEMBERS.get(v['member'], {}).get('weight', 1.0) for v in agrees)
    threshold    = VOTE_THRESHOLD

    passed    = agree_count >= threshold
    overruled = (len(disagrees) >= 3) if len(votes) >= 3 else False

    if passed:
        decision = 'APPROVED'
    elif overruled:
        decision = 'REJECTED'
    elif len(watches) >= 2:
        decision = 'WATCH'  # 多數觀望
    else:
        decision = 'NO_CONSENSUS'

    return {
        'agree_count':  agree_count,
        'disagree_count': len(disagrees),
        'abstain_count': len(abstains),
        'watch_count':   len(watches),
        'total_weight':  total_weight,
        'threshold':     threshold,
        'decision':      decision,
        'agrees':        agrees,
        'disagrees':     disagrees,
        'abstains':      abstains,
        'watches':       watches,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 報告輸出
# ═══════════════════════════════════════════════════════════════════════════

def format_vote_card(vote: Dict) -> str:
    member_info = MEMBERS.get(vote['member'], {})
    vote_t = vote['vote']
    icon = {'agree': '[+]', 'disagree': '[-]', 'abstain': '[=]', 'watch': '[@]'}.get(vote_t, '[?]')
    icon_str = {
        'agree':    f'\033[92m{icon}\033[0m',
        'disagree': f'\033[91m{icon}\033[0m',
        'abstain':  f'\033[90m{icon}\033[0m',
        'watch':    f'\033[93m{icon}\033[0m',
    }.get(vote_t, icon)
    conf = vote.get('confidence', 0)
    reason = vote.get('reason', 'N/A')
    tags = ','.join(vote.get('tags', [])) or 'none'
    # ASCII-safe output
    return (
        f"  {icon_str} **{vote['member']}**\n"
        f"     conf={conf}% | reason: {reason[:80]}\n"
        f"     tags: {tags}"
    )


def print_committee_report(symbol: str, action: str, strategy: str,
                           votes: List[Dict], tally: Dict):
    """輸出完整委員會報告"""
    action_cn = ACTION_LABELS.get(action, action)
    price = get_latest_price(symbol)
    price_str = f'${price:.2f}' if price else 'N/A'

    decision_color = {
        'APPROVED':     '\033[92m',
        'REJECTED':     '\033[91m',
        'WATCH':        '\033[93m',
        'NO_CONSENSUS': '\033[90m',
    }.get(tally['decision'], '')

    print()
    print('=' * 64)
    print(f'  [Committee Vote] {symbol} - {action} ({strategy})')
    print(f'  Time: {datetime.now().strftime("%Y-%m-%d %H:%M")} | Price: {price_str}')
    print('=' * 64)
    print()
    print('  [Member Votes]')
    for v in votes:
        try:
            print(format_vote_card(v))
        except Exception:
            m = v.get('member','?'); vo = v.get('vote','?'); cf = v.get('confidence',0); rs = v.get('reason','?')[:50]
            icon = {'agree':'[+]','disagree':'[-]','abstain':'[=]','watch':'[@]'}.get(vo,'[?]')
            print(f'  {icon} {m} | conf={cf}% | {rs}')
        print()

    print('  -- Summary --')
    print(f"  Agree={tally['agree_count']} / Disagree={tally['disagree_count']} / Abstain={tally['abstain_count']} / Watch={tally['watch_count']}")
    print(f"  Threshold: {tally['threshold']}/5")
    dec_color = '\033[92m' if tally['decision']=='APPROVED' else ('\033[91m' if tally['decision']=='REJECTED' else '\033[93m')
    print(f"  Result: {dec_color}{tally['decision']}\033[0m")
    print('  --')

    if tally['decision'] == 'APPROVED':
        print(f"\n  -> [APPROVED] Execute {action.upper()} {symbol} ({strategy})")
        print(f"     Confidence: {tally['total_weight']:.1f} / {tally['threshold']} (threshold)")
    elif tally['decision'] == 'REJECTED':
        print(f"\n  -> [REJECTED] Veto {action} {symbol}")
    elif tally['decision'] == 'WATCH':
        print(f"\n  -> [WATCH] Monitor {symbol}, do not execute")
    else:
        print(f"\n  -> [NO_CONSENSUS] No consensus, recommend skip")
    print()


def generate_vote_record(symbol: str, action: str, strategy: str,
                         votes: List[Dict], tally: Dict) -> Dict:
    """產生結構化投票記錄（可儲存）"""
    return {
        'timestamp':    datetime.now().isoformat(),
        'symbol':       symbol,
        'action':       action,
        'strategy':     strategy,
        'decision':     tally['decision'],
        'threshold':    tally['threshold'],
        'votes': [
            {
                'member':    v['member'],
                'vote':      v['vote'],
                'confidence': v.get('confidence', 0),
                'reason':    v.get('reason', ''),
                'tags':      v.get('tags', []),
            } for v in votes
        ],
        'tally': {
            'agree_count':   tally['agree_count'],
            'disagree_count': tally['disagree_count'],
            'abstain_count': tally['abstain_count'],
            'watch_count':   tally['watch_count'],
            'total_weight':  tally['total_weight'],
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Tina Decision Committee Vote')
    parser.add_argument('--action',   required=True,
                        help='操作類型：buy / sell / hold / watch / skip')
    parser.add_argument('--symbol',   required=True,
                        help='股票代碼（如 2330.TW）')
    parser.add_argument('--strategy', default='swing',
                        help='策略：swing / growth_long / dca / etf_trend')
    parser.add_argument('--save',     action='store_true',
                        help='儲存投票記錄到 JSON')
    parser.add_argument('--report',   action='store_true',
                        help='顯示近期投票記錄')
    args = parser.parse_args()

    action   = args.action.lower()
    symbol   = args.symbol.upper()
    strategy = args.strategy.lower()

    if action not in ACTION_LABELS:
        print(f'[ERROR] 未知操作：{action}，可用：{list(ACTION_LABELS.keys())}')
        return

    if strategy not in ('swing', 'growth_long', 'dca', 'etf_trend'):
        print(f'[ERROR] 未知策略：{strategy}')
        return

    print(f'\n[Committee] Starting vote: {action.upper()} {symbol} ({strategy})')

    votes = collect_votes(symbol, action, strategy)
    tally = tally_votes(votes)
    print_committee_report(symbol, action, strategy, votes, tally)

    if args.save:
        record = generate_vote_record(symbol, action, strategy, votes, tally)
        out_dir = WORKSPACE / 'data' / 'committee_votes'
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        out_file = out_dir / f'vote_{symbol.replace(".","_")}_{action}_{ts}.json'
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f'[SAVED] {out_file}')

        # 同時更新 MEMORY.md 最後投票記錄
        last_vote_file = WORKSPACE / 'data' / 'last_committee_vote.json'
        with open(last_vote_file, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()