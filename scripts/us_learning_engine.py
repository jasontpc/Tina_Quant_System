# -*- coding: utf-8 -*-
"""
US Learning Engine — Tina Quant System
主動學習分析模組：追蹤進場表現、調整篩選權重、產出學習報告
"""

import sqlite3
import json
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'us_value_growth.db')
BUY_LOG_CSV = os.path.join(DATA_DIR, 'us_buy_log.csv')
WEIGHTS_JSON = os.path.join(DATA_DIR, 'us_learning_weights.json')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Default filter weights ────────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    'filter_weights': {
        'pe':           {'weight': 20, 'optimal_min': 5,  'optimal_max': 20, 'penalty_above': 30},
        'rev_growth':   {'weight': 20, 'optimal_min': 0.10, 'optimal_max': None, 'penalty_below': 0},
        'op_margin':    {'weight': 15, 'optimal_min': 0.15, 'optimal_max': None},
        'roe':          {'weight': 15, 'optimal_min': 0.15, 'optimal_max': None},
        'debt_ratio':   {'weight': 10, 'optimal_max': 50, 'penalty_above': 80},
        'div_yield':    {'weight': 10, 'optimal_min': 0.02, 'optimal_max': None},
        'rsi':          {'weight': 20, 'optimal_min': 35, 'optimal_max': 60},
        'bias20':       {'weight': 10, 'optimal_max': 8},
        'vol_surge':    {'weight': 10, 'optimal_min': 1.5},
        'ma_aligned':   {'weight': 15, 'optimal_min': 2, 'optimal_max': 3},  # 1=P>MA5, 2=P>MA5>MA20, 3=P>MA5>MA20>MA60
    },
    'stock_overrides': {}
}

# ── Init CSV ─────────────────────────────────────────────────────────────────
def init_buy_log():
    if not os.path.exists(BUY_LOG_CSV):
        with open(BUY_LOG_CSV, 'w', encoding='utf-8') as f:
            f.write('id,date,time,symbol,entry_price,quantity,cost_basis,reason,score,rsi_entry,expected_return_pct,stop_loss_pct,notes,status,exit_date,exit_price,realized_return_pct,exit_reason\n')

def next_log_id():
    if not os.path.exists(BUY_LOG_CSV):
        return 1
    with open(BUY_LOG_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) <= 1:
        return 1
    return int(lines[-1].split(',')[0]) + 1

# ── Record a buy ──────────────────────────────────────────────────────────────
def record_buy(symbol, entry_price, quantity, reason, score, rsi_entry,
               expected_return_pct=0.15, stop_loss_pct=0.08, notes=''):
    init_buy_log()
    nid = next_log_id()
    now = datetime.now()
    date = now.strftime('%Y-%m-%d')
    time = now.strftime('%H:%M')
    cost_basis = entry_price * quantity
    with open(BUY_LOG_CSV, 'a', encoding='utf-8') as f:
        f.write(
            f'{nid},{date},{time},{symbol},{entry_price:.2f},{quantity},'
            f'{cost_basis:.2f},"{reason}",{score},{rsi_entry:.1f},'
            f'{expected_return_pct*100:.1f},{stop_loss_pct*100:.1f},'
            f'"{notes}",OPEN,,\n'
        )
    print(f'  [LOG] Buy recorded: {symbol} @ ${entry_price:.2f} x{quantity}')

# ── Record a sell / close ─────────────────────────────────────────────────────
def record_sell(symbol, exit_price, exit_reason='target'):
    init_buy_log()
    rows = []
    with open(BUY_LOG_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    header = lines[0]
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) >= 15 and parts[3] == symbol and parts[14] == 'OPEN':
            entry_price = float(parts[4])
            quantity = int(parts[6])
            expected_return = float(parts[11]) / 100
            realized = (exit_price / entry_price - 1) * 100
            exit_date = datetime.now().strftime('%Y-%m-%d')
            parts[14] = 'CLOSED'
            parts[15] = exit_date
            parts[16] = f'{exit_price:.2f}'
            parts[17] = f'{realized:.2f}'
            parts[18] = exit_reason
            line = ','.join(parts)
        rows.append(line)
    with open(BUY_LOG_CSV, 'w', encoding='utf-8') as f:
        f.write(header)
        f.writelines(rows)
    print(f'  [LOG] Sell recorded: {symbol} @ ${exit_price:.2f}, realized={realized:.2f}%')

# ── Check open positions & update status ───────────────────────────────────────
def update_open_positions():
    """Check if any open positions have hit stop loss or profit target"""
    if not os.path.exists(BUY_LOG_CSV):
        return []
    rows = []
    with open(BUY_LOG_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    header = lines[0]
    closed = []
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) < 19 or parts[14] != 'OPEN':
            rows.append(line)
            continue
        symbol = parts[3]
        entry_price = float(parts[4])
        stop_loss_pct = float(parts[13]) / 100
        target_pct = float(parts[12]) / 100
        try:
            ticker = yf.Ticker(symbol)
            h = ticker.history(period='5d')
            if h.empty:
                rows.append(line)
                continue
            current_price = float(h['Close'].iloc[-1])
            ret = (current_price / entry_price - 1)
            stop_loss = 1 - stop_loss_pct
            if ret <= -stop_loss_pct:
                parts[14] = 'CLOSED'
                parts[15] = datetime.now().strftime('%Y-%m-%d')
                parts[16] = f'{current_price:.2f}'
                parts[17] = f'{ret*100:.2f}'
                parts[18] = 'stop_loss'
                closed.append((symbol, 'STOP_LOSS', ret*100))
            elif ret >= target_pct:
                parts[14] = 'CLOSED'
                parts[15] = datetime.now().strftime('%Y-%m-%d')
                parts[16] = f'{current_price:.2f}'
                parts[17] = f'{ret*100:.2f}'
                parts[18] = 'profit_target'
                closed.append((symbol, 'PROFIT_TARGET', ret*100))
            else:
                rows.append(line)
                continue
        except Exception:
            rows.append(line)
            continue
        rows.append(','.join(parts))
    with open(BUY_LOG_CSV, 'w', encoding='utf-8') as f:
        f.write(header)
        f.writelines(rows)
    if closed:
        print(f'  [LOG] Auto-closed {len(closed)} positions: {closed}')
    return closed

# ── Load / save weights ───────────────────────────────────────────────────────
def load_weights():
    if os.path.exists(WEIGHTS_JSON):
        with open(WEIGHTS_JSON, 'r') as f:
            return json.load(f)
    return DEFAULT_WEIGHTS.copy()

def save_weights(weights):
    with open(WEIGHTS_JSON, 'w') as f:
        json.dump(weights, f, indent=2)

# ── Parse buy log into DataFrame ──────────────────────────────────────────────
def load_buy_log_df():
    if not os.path.exists(BUY_LOG_CSV):
        return pd.DataFrame()
    df = pd.read_csv(BUY_LOG_CSV)
    if df.empty:
        return df
    df['entry_price'] = pd.to_numeric(df['entry_price'], errors='coerce')
    df['exit_price'] = pd.to_numeric(df['exit_price'], errors='coerce')
    df['realized_return_pct'] = pd.to_numeric(df['realized_return_pct'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
    return df

# ── Analyze performance ───────────────────────────────────────────────────────
def analyze_performance(days_back=30):
    df = load_buy_log_df()
    cutoff = datetime.now() - timedelta(days=days_back)
    recent = df[df['date'] >= cutoff] if not df.empty else df

    total = len(recent[recent['status'] == 'CLOSED'])
    wins = len(recent[(recent['status'] == 'CLOSED') & (recent['realized_return_pct'] > 0)])
    winrate = wins / total if total > 0 else 0

    avg_ret = recent[recent['status'] == 'CLOSED']['realized_return_pct'].mean()
    avg_hold_days = None
    if not recent.empty:
        closed = recent[recent['status'] == 'CLOSED'].copy()
        if not closed.empty and 'exit_date' in closed.columns:
            closed['hold_days'] = (closed['exit_date'] - closed['date']).dt.days
            avg_hold_days = closed['hold_days'].mean()

    # Per-symbol breakdown
    sym_stats = {}
    if not recent.empty:
        for sym, grp in recent[recent['status'] == 'CLOSED'].groupby('symbol'):
            ret = grp['realized_return_pct'].mean()
            cnt = len(grp)
            sym_stats[sym] = {'avg_return': ret, 'count': cnt, 'winrate': len(grp[grp['realized_return_pct'] > 0]) / cnt if cnt > 0 else 0}

    # Failure patterns
    failures = recent[(recent['status'] == 'CLOSED') & (recent['realized_return_pct'] < 0)]
    failure_reasons = defaultdict(int)
    for _, row in failures.iterrows():
        if pd.notna(row.get('exit_reason')):
            failure_reasons[row['exit_reason']] += 1
        else:
            failure_reasons['unknown'] += 1

    return {
        'period_days': days_back,
        'total_trades': total,
        'wins': wins,
        'winrate': winrate,
        'avg_return_pct': avg_ret,
        'avg_hold_days': avg_hold_days,
        'per_symbol': sym_stats,
        'failure_reasons': dict(failure_reasons),
        'open_positions': len(recent[recent['status'] == 'OPEN'])
    }

# ── Adjust weights based on performance ───────────────────────────────────────
def adjust_weights(perf):
    weights = load_weights()
    fw = weights['filter_weights']

    for sym, stats in perf.get('per_symbol', {}).items():
        if stats['count'] < 2:
            continue
        ret = stats['avg_return']
        wr = stats['winrate']
        # If a stock consistently wins with high return, boost its criteria weight
        if ret > 10 and wr >= 0.7:
            for k in fw:
                fw[k]['weight'] = min(fw[k]['weight'] * 1.05, fw[k]['weight'] * 1.5)
        # If a stock consistently loses, reduce weight / tighten entry
        elif ret < -5 or wr < 0.4:
            for k in fw:
                fw[k]['weight'] = max(fw[k]['weight'] * 0.95, fw[k]['weight'] * 0.5)
            # Tighten RSI entry for that stock
            if sym in weights.get('stock_overrides', {}):
                weights['stock_overrides'][sym]['rsi_tighter'] = True
            else:
                weights.setdefault('stock_overrides', {})[sym] = {'rsi_tighter': True}

    save_weights(weights)
    return weights

# ── Generate monthly learning report ─────────────────────────────────────────
def generate_learning_report():
    perf_30 = analyze_performance(30)
    perf_90 = analyze_performance(90)

    report = []
    report.append('# 📚 US Learning Report')
    report.append(f'__{datetime.now().strftime("%Y-%m-%d")}__')
    report.append('')

    for period_name, perf in [('30D', perf_30), ('90D', perf_90)]:
        if perf['total_trades'] == 0:
            continue
        report.append(f'## 📊 {period_name} 學習統計')
        report.append(f'- 總交易筆數: {perf["total_trades"]}')
        report.append(f'- 勝利次數: {perf["wins"]}')
        report.append(f'- 勝率: {perf["winrate"]*100:.1f}%')
        report.append(f'- 平均報酬: {perf["avg_return_pct"]:.2f}%' if perf['avg_return_pct'] else '- 平均報酬: N/A')
        report.append(f'- 平均持有天數: {perf["avg_hold_days"]:.1f}' if perf['avg_hold_days'] else '- 平均持有天數: N/A')
        report.append(f'- 開倉中: {perf["open_positions"]} 檔')

        if perf['per_symbol']:
            report.append('')
            report.append(f'| 代號 | 筆數 | 勝率 | 平均報酬 |')
            report.append('|:----:|:----:|:----:|:--------:|')
            for sym, s in sorted(perf['per_symbol'].items(), key=lambda x: x[1]['avg_return'], reverse=True):
                wr = s['winrate'] * 100
                ret = s['avg_return']
                report.append(f'| {sym} | {s["count"]} | {wr:.0f}% | {ret:+.2f}% |')

        if perf['failure_reasons']:
            report.append('')
            report.append('### ❌ 失敗原因分析')
            for reason, cnt in sorted(perf['failure_reasons'].items(), key=lambda x: x[1], reverse=True):
                report.append(f'- {reason}: {cnt} 次')

        report.append('')

    # Recommendations
    report.append('## 💡 優化建議')
    perf = perf_30
    if perf['winrate'] < 0.5:
        report.append('- ⚠️ 勝率低於 50%，建議提高 RSI 進場標準')
    if perf['avg_return_pct'] and perf['avg_return_pct'] < 5:
        report.append('- ⚠️ 平均報酬過低，建議調整停利區間')
    if perf['failure_reasons'].get('stop_loss', 0) > perf['total_trades'] * 0.3:
        report.append('- ⚠️ 停損觸發過多，建議擴大 ATR 停損百分比')

    weights = load_weights()
    report.append('')
    report.append('### 🔧 目前篩選權重')
    for k, v in weights['filter_weights'].items():
        report.append(f'- {k}: weight={v["weight"]}')

    path = os.path.join(REPORTS_DIR, f'us_learning_report_{datetime.now().strftime("%Y%m%d")}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print(f'  [REPORT] Saved: {path}')
    return path

# ── Score a stock using current weights ───────────────────────────────────────
def score_with_weights(symbol):
    w = load_weights()
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='6mo')
        if h.empty or len(h) < 30:
            return None
        info = t.info or {}
        price = float(h['Close'].iloc[-1])
        closes = h['Close'].tolist()
        rsi = _calc_rsi(closes, 14)
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        bias20 = (price / ma20 - 1) * 100
        ma_aligned = 3 if price > ma5 > ma20 > ma60 else (2 if price > ma5 > ma20 else (1 if price > ma5 else 0))
        vol_now = h['Volume'].iloc[-1]
        vol_avg = h['Volume'].rolling(20).mean().iloc[-1]
        vol_surge = vol_now / vol_avg if vol_avg > 0 else 0

        pe = info.get('trailingPE', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        op_margin = info.get('operatingMargins', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        debt_ratio = info.get('debtToEquity', 50) or 50
        div_yield = info.get('dividendYield', 0) or 0

        fw = w['filter_weights']
        score = 0
        # PE
        if 5 <= pe <= 20:
            score += fw['pe']['weight']
        elif 20 < pe <= 30:
            score += fw['pe']['weight'] * 0.5
        elif pe > 30:
            score += fw['pe']['weight'] * 0.2
        # rev_growth
        if rev_growth >= 0.10:
            score += fw['rev_growth']['weight']
        elif rev_growth >= 0.05:
            score += fw['rev_growth']['weight'] * 0.7
        elif rev_growth >= 0:
            score += fw['rev_growth']['weight'] * 0.3
        # op_margin
        if op_margin >= 0.15:
            score += fw['op_margin']['weight']
        elif op_margin >= 0.10:
            score += fw['op_margin']['weight'] * 0.7
        # roe
        if roe >= 0.15:
            score += fw['roe']['weight']
        elif roe >= 0.08:
            score += fw['roe']['weight'] * 0.7
        # debt_ratio
        if debt_ratio <= 50:
            score += fw['debt_ratio']['weight']
        elif debt_ratio <= 80:
            score += fw['debt_ratio']['weight'] * 0.5
        # div_yield
        if div_yield >= 0.02:
            score += fw['div_yield']['weight']
        # RSI
        if 35 <= rsi <= 60:
            score += fw['rsi']['weight']
        elif 30 <= rsi < 35:
            score += fw['rsi']['weight'] * 0.7
        # bias20
        if abs(bias20) < 8:
            score += fw['bias20']['weight']
        elif abs(bias20) < 12:
            score += fw['bias20']['weight'] * 0.5
        # vol_surge
        if vol_surge >= 1.5:
            score += fw['vol_surge']['weight']
        elif vol_surge >= 1.2:
            score += fw['vol_surge']['weight'] * 0.5
        # ma_aligned
        if ma_aligned >= 2:
            score += fw['ma_aligned']['weight']
        elif ma_aligned == 1:
            score += fw['ma_aligned']['weight'] * 0.5

        return score
    except Exception as e:
        print(f'  [WARN] score_with_weights {symbol}: {e}')
        return None

def _calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    deltas = pd.Series(prices).diff()
    gain = deltas.where(deltas > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-deltas.where(deltas < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])

# ── Main run ──────────────────────────────────────────────────────────────────
def run():
    print('='*60)
    print('US Learning Engine')
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)

    # 1. Update open positions
    print('\n[1] Checking open positions...')
    closed = update_open_positions()

    # 2. Analyze recent performance
    print('\n[2] Analyzing performance...')
    perf = analyze_performance(30)
    print(f'  30D: {perf["total_trades"]} trades, winrate={perf["winrate"]*100:.1f}%, avg_ret={perf["avg_return_pct"]:.2f}%' if perf['total_trades'] > 0 else '  No closed trades in 30D')

    # 3. Adjust weights
    print('\n[3] Adjusting filter weights...')
    adjust_weights(perf)

    # 4. Generate learning report
    print('\n[4] Generating monthly report...')
    report_path = generate_learning_report()

    print('\n[5] Top candidates by adjusted score...')
    candidates = ['D','BMY','SO','DXCM','FITB','HBAN','CARG','NEE','SWKS','CVLT','SCHW','SLB','NET','MU','AVGO']
    scored = []
    for sym in candidates:
        s = score_with_weights(sym)
        if s:
            scored.append((sym, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    for sym, sc in scored[:10]:
        print(f'  {sym}: score={sc:.1f}')

    print('\n' + '='*60)
    print('DONE')
    return {'performance': perf, 'report_path': report_path, 'top_candidates': scored[:10]}

if __name__ == '__main__':
    run()
