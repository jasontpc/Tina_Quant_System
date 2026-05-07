"""Leo Daily Paper Trade Review — TW + US 雙市場版
整合 tina_think 慢思考引擎

用法：
  python leos_daily_review.py              # AUTO_THINK：自動執行（事後補日誌）
  python leos_daily_review.py --think      # FULL_THINK：發報告→等回應→執行
  python leos_daily_review.py --fast       # FAST_TRACK：直接執行（緊急模式）
  python leos_daily_review.py --status     # 只看狀態，不做任何操作
"""
import sys, json, os, time, yfinance as yf, re
import numpy as np
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
ANALYSIS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_analysis_v65.json'
DECISION_LOG = os.path.expanduser('~/.openclaw/workspace/memory/decision_log.md')

# === 專家委員會常量（從 tina_think.py 移植）===
EXPERT_WEIGHTS = {'quant': 0.35, 'dev': 0.35, 'risk': 0.30}
TWII_HOT_RSI = 85
MAX_POSITIONS_PER_STOCK = 3

# === 固定規則 ===
MAX_HOLD_DAYS = 45
OVERBOUGHT_PROFIT_LOCK_PCT = 5.0
OVERBOUGHT_EXIT_RSI = 80
BIG_GAIN_TAKE_PROFIT_PCT = 15.0
US_TAKE_PROFIT_AMOUNT = 300
US_STOP_LOSS_AMOUNT = 200
TRAILING_PROFIT_PCT = 5.0
FORCE_REDUCE_DAYS = 10
FORCE_REDUCE_PCT = 0.5
FEE_RATE = 0.004

# === Telegram ===
TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = '1616824689'

# === 分析模式 ===
MODE_FULL_THINK = 'full_think'
MODE_AUTO_THINK = 'auto_think'
MODE_FAST_TRACK = 'fast_track'
MODE_STATUS = 'status'

# === 台美股池 ===
US_STOCKS = ['NVDA', 'AMD', 'QCOM', 'ARM', 'MU', 'WDC', 'STX',
             'ANET', 'LITE', 'COHR', 'AMZN', 'MSFT', 'GOOGL', 'META',
             'AMAT', 'LRCX', 'KLAC', 'SNPS', 'ASML', 'MRVL', 'AVGO']

# ============================================================
# 工具函數
# ============================================================
def get_rsi(closes, period=12):
    if len(closes) < period + 1: return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 50

def get_twii_rsi():
    try:
        t = yf.Ticker('^TWII').history(period='20d')
        if len(t) >= 13:
            return get_rsi(t['Close'].dropna().values, 12)
    except: pass
    return 50

def send_telegram(text):
    """發送 Telegram 報告"""
    if not TELEGRAM_TOKEN:
        print(f'[TG] {text[:300]}')
        return True
    import urllib.request
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        print(f'Telegram failed: {e}')
        return False

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'trades': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_decision(sym, mkt, decision, reason, pnl_pct, mode):
    """寫入決策日誌"""
    ts = time.strftime('%Y-%m-%d %H:%M')
    entry = f"""
### [{ts}] 決策：{sym}（{mkt}）— {reason}

**模式：** {mode}
**委員會決定：** {decision}
**損益：** {pnl_pct:+.2f}%

---
"""
    try:
        os.makedirs(os.path.dirname(DECISION_LOG), exist_ok=True)
        with open(DECISION_LOG, 'a', encoding='utf-8') as f:
            f.write(entry)
    except: pass

# ============================================================
# 專家委員會（從 tina_think.py 移植優化）
# ============================================================
def get_stock_score_data(sym, mkt, current_price, rsi):
    """針對持倉股票，快速獲取評分所需數據"""
    suffix = '.TW' if mkt == 'TW' else ''
    try:
        t = yf.Ticker(f'{sym}{suffix}').history(period='30d')
        if t.empty:
            return {}
        closes = t['Close'].dropna().values
        if len(closes) < 20:
            return {}
        ma20 = np.mean(closes[-20:])
        mom5 = (closes[-1] / closes[-5] - 1) * 100 if len(closes) >= 6 else 0
        mom20 = (closes[-1] / closes[-20] - 1) * 100 if len(closes) >= 21 else 0
        pos_ma20 = (current_price - ma20) / ma20 * 100 if ma20 != 0 else 0
        return {'rsi': rsi, 'mom5': mom5, 'mom20': mom20,
                'pos_ma20': pos_ma20, 'ma20': ma20}
    except:
        return {}

def expert_committee_for_exit(sym, mkt, stock_data, open_positions, twii_rsi, pnl_pct, days_held):
    """單一持倉的專家委員會分析（用於出场決策）"""
    # 量化分析師
    q_score = 50
    q_signals = []
    rsi = stock_data.get('rsi', 50)
    if rsi > OVERBOUGHT_EXIT_RSI:
        q_score -= 20; q_signals.append(f'RSI {rsi:.0f} 過熱')
    elif rsi < 40:
        q_score += 20; q_signals.append('RSI 超賣')
    else:
        q_score += 5; q_signals.append(f'RSI {rsi:.0f} 中性')

    mom5 = stock_data.get('mom5', 0)
    if mom5 > 5: q_score += 15; q_signals.append('動量強')
    elif mom5 < -3: q_score -= 10; q_signals.append('動量弱')

    q_verdict = 'SELL' if q_score < 40 else ('HOLD' if q_score < 60 else 'BUY')

    # 資深開發者
    d_score = 50
    d_signals = []
    pos_ma20 = stock_data.get('pos_ma20', 0)
    if pos_ma20 > 15: d_score -= 15; d_signals.append('MA20偏離過大')
    elif pos_ma20 < 0: d_score -= 10; d_signals.append('跌破MA20')

    if twii_rsi > TWII_HOT_RSI:
        d_score -= 10; d_signals.append(f'TWII RSI {twii_rsi:.0f} 過熱')
    if pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
        d_score += 15; d_signals.append(f'盈利 {pnl_pct:.1f}% 達目標')

    d_verdict = 'SELL' if d_score < 35 else ('HOLD' if d_score < 55 else 'BUY')

    # 風控長
    r_score = 50
    r_signals = []
    same_stock_count = sum(1 for t in open_positions
                           if t['symbol'] == sym and t.get('market', 'TW') == mkt and t.get('status') == 'open')
    if same_stock_count >= 3:
        r_score -= 25; r_signals.append(f'已達3口上限')
    elif same_stock_count >= 2:
        r_score -= 10; r_signals.append(f'已有{same_stock_count}口')

    if pnl_pct <= -5:
        r_score -= 15; r_signals.append(f'虧損 {pnl_pct:.1f}% 注意')
    elif pnl_pct >= 10:
        r_score += 10; r_signals.append(f'盈利 {pnl_pct:.1f}% 紀律持倉')

    if days_held >= FORCE_REDUCE_DAYS and pnl_pct < 5:
        r_score -= 10; r_signals.append('持有10天未達目標')

    r_verdict = 'SELL' if r_score < 40 else ('HOLD' if r_score < 50 else 'BUY')

    # 加權總分
    total = q_score * 0.35 + d_score * 0.35 + r_score * 0.30

    # 委員會決定
    verdicts = [q_verdict, d_verdict, r_verdict]
    if verdicts.count('SELL') >= 2:
        decision = 'EXIT'
    elif verdicts.count('HOLD') >= 2:
        decision = 'HOLD'
    else:
        decision = 'KEEP'

    return {
        'total_score': round(total, 1),
        'decision': decision,
        'q': {'score': q_score, 'verdict': q_verdict, 'signals': q_signals},
        'd': {'score': d_score, 'verdict': d_verdict, 'signals': d_signals},
        'r': {'score': r_score, 'verdict': r_verdict, 'signals': r_signals},
    }

def generate_exit_report(sym, mkt, entry, cur, target, stop, rsi, pnl_pct, pnl_abs,
                         days_held, reason, committee, mode):
    """生成出场慢思考報告"""
    emoji = '🔴' if pnl_pct < 0 else ('🟢' if pnl_pct > 0 else '⚪')
    lines = [
        f'{emoji} *Leo 出场慢思考報告*',
        '=' * 40,
        f'📌 *{sym} {mkt}*',
        f'⏰ {time.strftime("%Y-%m-%d %H:%M")}',
        '',
        f'💰 *持倉狀態*',
        f'  進場：${entry:.2f} → 現在：${cur:.2f}',
        f'  損益：{pnl_pct:+.1f}%（${pnl_abs:+,.0f}）',
        f'  持有：{days_held:.0f}天',
        f'  目標：${target:.2f} | 停損：${stop:.2f}',
        '',
        f'🔍 *專家委員會*',
        f'  📈 量化分析師（35%）：{committee["q"]["verdict"]} — {committee["q"]["score"]}分',
        f'     {"｜".join(committee["q"]["signals"][:2])}',
        f'  ⚙️ 資深開發者（35%）：{committee["d"]["verdict"]} — {committee["d"]["score"]}分',
        f'     {"｜".join(committee["d"]["signals"][:2])}',
        f'  🛡️ 風控長（30%）：{committee["r"]["verdict"]} — {committee["r"]["score"]}分',
        f'     {"｜".join(committee["r"]["signals"][:2])}',
        '',
        f'  🔗 加權總分：{committee["total_score"]}分',
        f'  🏛️ 委員會決定：{committee["decision"]}',
        '',
    ]

    if reason:
        lines.append(f'📋 *触发原因：{reason}*')

    if mode == MODE_FULL_THINK:
        lines.append('🔔 *等待 Jo 確認中...（回覆 `confirm` 執行 / `reject` 否決）*')
    elif mode == MODE_AUTO_THINK:
        lines.append('🤖 [Auto Think] 自動執行中')
    else:
        lines.append('⚡ [Fast Track] 直接執行')

    return '\n'.join(lines)

def generate_entry_report(sym, name, mkt, price, rsi, score, target, stop, twii_rsi, committee, mode):
    """生成進場慢思考報告"""
    hot = twii_rsi > TWII_HOT_RSI
    pos_scale = 0.5 if hot else 1.0
    lines = [
        f'🧠 *Leo 進場慢思考報告*',
        '=' * 40,
        f'📌 *{sym} {name}*（{mkt}）',
        f'⏰ {time.strftime("%Y-%m-%d %H:%M")}',
        '',
        f'📊 *市場環境*',
        f'  TWII RSI: `{twii_rsi:.0f}` {"🔥 過熱" if hot else "✅ 正常"}',
        f'  部位調整: {"×0.5（降50%）" if pos_scale < 1 else "×1.0（全倉）"}',
        '',
        f'🔍 *專家委員會*',
        f'  📈 量化分析師（35%）：{committee["q"]["verdict"]} — {committee["q"]["score"]}分',
        f'     {"｜".join(committee["q"]["signals"][:2])}',
        f'  ⚙️ 資深開發者（35%）：{committee["d"]["verdict"]} — {committee["d"]["score"]}分',
        f'     {"｜".join(committee["d"]["signals"][:2])}',
        f'  🛡️ 風控長（30%）：{committee["r"]["verdict"]} — {committee["r"]["score"]}分',
        f'     {"｜".join(committee["r"]["signals"][:2])}',
        '',
        f'  🔗 加權總分：{committee["total_score"]}分',
        f'  🏛️ 委員會決定：{committee["decision"]}',
        '',
        f'💡 *建議：目標 ${target:.0f} / 停損 ${stop:.0f}*',
        f'`RSI {rsi:.0f} | Score {score} | {"小倉位" if pos_scale<1 else "正常倉位"}`',
    ]

    if mode == MODE_FULL_THINK:
        lines.append('🔔 *等待 Jo 確認中...（回覆 `confirm` 執行 / `reject` 否決）*')
    elif mode == MODE_AUTO_THINK:
        lines.append('🤖 [Auto Think] 自動執行中')
    else:
        lines.append('⚡ [Fast Track] 直接執行')

    return '\n'.join(lines)

# ============================================================
# 價格取得
# ============================================================
def get_current_prices():
    prices = {}
    # TW
    tw_syms = ['2330', '2454', '2317', '2382', '3034', '2376', '2379', '3665']
    for sym in tw_syms:
        try:
            t = yf.Ticker(f'{sym}.TW').history(period='2d')
            if not t.empty and len(t['Close']) >= 2:
                closes = t['Close'].dropna().values
                prices[('TW', sym)] = {'price': float(closes[-1]), 'rsi': get_rsi(closes, 12)}
        except: pass
    # US
    for sym in US_STOCKS:
        try:
            t = yf.Ticker(sym).history(period='2d')
            if not t.empty and len(t['Close']) >= 2:
                closes = t['Close'].dropna().values
                prices[('US', sym)] = {'price': float(closes[-1]), 'rsi': get_rsi(closes, 12)}
        except: pass
    return prices

# ============================================================
# 核心：每日檢討
# ============================================================
def run_daily_review(mode=MODE_AUTO_THINK):
    print('=' * 60)
    mode_label = {
        MODE_FULL_THINK: 'FULL_THINK（報告→等回應→執行）',
        MODE_AUTO_THINK: 'AUTO_THINK（自動執行）',
        MODE_FAST_TRACK: 'FAST_TRACK（直接執行）',
        MODE_STATUS: 'STATUS ONLY（僅查看）',
    }.get(mode, mode)
    print(f'Leo Daily Review — {mode_label}')
    print('Time:', time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    trades_data = load_trades()
    open_t = [t for t in trades_data['trades'] if t.get('status') == 'open']
    closed_t = [t for t in trades_data['trades'] if t.get('status') == 'closed']

    print(f'\n📊 持倉：Open {len(open_t)} | Closed {len(closed_t)}')

    # TWII
    twii_rsi = get_twii_rsi()
    print(f'  TWII RSI: {twii_rsi:.0f} {"🔥 過熱" if twii_rsi > TWII_HOT_RSI else "✅"}')

    if mode == MODE_STATUS:
        # 只看狀態，不執行任何操作
        print('\n[Status Only Mode]')
        if open_t:
            print(f'\n  Open positions:')
            for t in open_t[:10]:
                mkt = t.get('market', 'TW')
                print(f'    {mkt}:{t["symbol"]} x{t.get("shares",0)} @ ${t["entry_price"]:.0f}')
        return

    # Current prices
    print('\n[Step 1] 取得即時價格...')
    current = get_current_prices()
    print(f'  已取得 {len(current)} 檔價格')

    # ========== 出場決策 ==========
    print('\n[Step 2] 出場決策分析...')
    exits_to_run = []
    overbought_profit = []

    for t in open_t:
        sym = t['symbol']
        mkt = t.get('market', 'TW')
        key = (mkt, sym)

        if key not in current:
            print(f'  {mkt}:{sym}: 無價格資料，跳過')
            continue

        cur = current[key]['price']
        entry = t['entry_price']
        shares = t.get('shares', 0)
        target = t.get('target_price', entry * 1.15 if mkt == 'TW' else entry * 1.15)
        stop = t.get('stop_loss', entry * 0.90 if mkt == 'TW' else entry - 10)
        rsi = current[key]['rsi']
        pnl_pct = (cur - entry) / entry * 100
        pnl_abs = (cur - entry) * shares

        try:
            entry_time = time.mktime(time.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S'))
            days_held = (time.time() - entry_time) / 86400
        except:
            days_held = 0

        reason = None

        # 停利/停損檢查
        if mkt == 'US':
            target_15pct_abs = (entry * 0.15) * shares
            us_tp = min(US_TAKE_PROFIT_AMOUNT, target_15pct_abs)
            if pnl_abs >= us_tp:
                reason = 'take_profit_us_15pct_or_300'
            elif pnl_abs <= -US_STOP_LOSS_AMOUNT:
                reason = 'stop_loss_us'
            elif rsi > 85 and pnl_pct > 3:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'
            if reason is None and pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry
                t['trailing_stop_active'] = True
                print(f'    [TRAILING STOP] {sym}: 停損 -> ${entry}')
            elif reason is None and t.get('trailing_stop_active') and cur <= t.get('trailing_stop', stop):
                reason = 'trailing_stop_triggered'
        else:
            if cur >= target:
                reason = 'take_profit_target'
            elif cur <= stop:
                reason = 'stop_loss'
            elif pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry
                t['trailing_stop_active'] = True
                print(f'    [TRAILING STOP] {sym}: 停損 -> ${entry}')
            elif t.get('trailing_stop_active') and cur <= t.get('trailing_stop', stop):
                reason = 'trailing_stop_triggered'
            elif rsi > OVERBOUGHT_EXIT_RSI and pnl_pct > OVERBOUGHT_PROFIT_LOCK_PCT:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'

        # 持有10天未達目標強制減倉
        if reason is None and days_held >= FORCE_REDUCE_DAYS and pnl_pct < 5 and not t.get('reduced_once'):
            new_shares = int(shares * FORCE_REDUCE_PCT)
            if new_shares >= 1:
                t['shares'] = new_shares
                t['amount'] = round(new_shares * cur, 0)
                t['reduced_once'] = True
                t['exit_reason'] = f'force_reduce_day10_pnl{pnl_pct:.1f}pct'
                if t.get('trailing_stop_active'):
                    t['trailing_stop'] = max(entry, t.get('trailing_stop', entry))
                print(f'  [減倉] {sym}: {shares}->{new_shares} shares (day10, pnl={pnl_pct:+.1f}%)')
                reason = 'force_reduce'
                exits_to_run.append((t, 'force_reduce', cur, pnl_pct, pnl_abs))

        # 通用條件
        if reason is None and pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
            reason = f'big_gain_take_profit_{pnl_pct:.1f}'
        elif reason is None and days_held > MAX_HOLD_DAYS:
            reason = f'max_hold_days_{days_held:.0f}'

        # 打印持倉狀態
        print(f'\n  {mkt}:{sym} {t.get("name","")}')
        print(f'    {entry:.0f} -> {cur:.0f} ({pnl_pct:+.1f}%) RSI={rsi:.0f} @{days_held:.0f}天')

        # 生成並發送慢思考報告
        stock_data = get_stock_score_data(sym, mkt, cur, rsi)
        committee = expert_committee_for_exit(sym, mkt, stock_data, open_t, twii_rsi, pnl_pct, days_held)

        if reason:
            print(f'    >>> 出场触发：{reason}（委員會：{committee["decision"]} {committee["total_score"]}分）')
            # 發送慢思考報告
            report = generate_exit_report(sym, mkt, entry, cur, target, stop, rsi, pnl_pct,
                                          pnl_abs, days_held, reason, committee, mode)
            send_telegram(report)

            if mode == MODE_FULL_THINK:
                # 等待確認（這裡是 Cron，所以實際上仍自動執行但發報告）
                print(f'    [FULL_THINK] 等待確認中...')
            else:
                exits_to_run.append((t, reason, cur, pnl_pct, pnl_abs))
        elif pnl_pct > 5:
            overbought_profit.append((f'{mkt}:{sym}', pnl_pct, rsi, (target - cur) / cur * 100))

    # 執行出场
    if mode != MODE_STATUS:
        print(f'\n[Step 3] 執行 {len(exits_to_run)} 筆出场...')
        for t, reason, cur, pnl_pct, pnl_abs in exits_to_run:
            entry = t['entry_price']
            shares = t.get('shares', 0)
            fee = round(entry * shares * FEE_RATE + cur * shares * FEE_RATE, 0)
            net_pnl = pnl_abs - fee
            mkt = t.get('market', 'TW')
            t['status'] = 'closed'
            t['exit_price'] = cur
            t['exit_reason'] = reason
            t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            t['pnl'] = round(net_pnl, 0)
            t['pnl_pct'] = round((cur - entry) / entry * 100 - FEE_RATE * 200, 2)
            t['fee'] = fee
            print(f'  出场 {mkt}:{t["symbol"]}: {reason} -> ${cur:.2f} ({pnl_pct:+.1f}%)')
            log_decision(t['symbol'], mkt, committee.get('decision', 'EXIT'), reason, pnl_pct, mode)

    # ==========  excess positions ==========
    print('\n[Step 4] 檢查部位集中度...')
    open_now = [t for t in trades_data['trades'] if t.get('status') == 'open']
    sym_counts = Counter((t.get('market', 'TW'), t['symbol']) for t in open_now)
    for (mkt, sym), count in sym_counts.items():
        if count > MAX_POSITIONS_PER_STOCK:
            print(f'\n  ⚠️ {mkt}:{sym} 有 {count} 口 — 超出上限 {MAX_POSITIONS_PER_STOCK}')
            same_sym = [t for t in open_now
                        if t.get('market', 'TW') == mkt and t['symbol'] == sym]
            same_sym.sort(key=lambda x: x.get('timestamp', ''))
            excess = count - MAX_POSITIONS_PER_STOCK
            for t in same_sym[:excess]:
                key = (mkt, sym)
                cur_p = current.get(key, {}).get('price', t['entry_price'])
                pnl_pct = (cur_p - t['entry_price']) / t['entry_price'] * 100
                pnl_abs = (cur_p - t['entry_price']) * t.get('shares', 0)
                fee = round(t['entry_price'] * t['shares'] * FEE_RATE + cur_p * t['shares'] * FEE_RATE, 0)
                net_pnl = pnl_abs - fee
                t['status'] = 'closed'
                t['exit_price'] = cur_p
                t['exit_reason'] = 'excess_positions_reduced'
                t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                t['pnl'] = round(net_pnl, 0)
                t['pnl_pct'] = round(pnl_pct - FEE_RATE * 200, 2)
                t['fee'] = fee
                print(f'  平倉 {sym}（excess）: ${t["entry_price"]:.0f}->${cur_p:.0f} ({pnl_pct:+.1f}%)')
                log_decision(sym, mkt, 'EXCESS', 'excess_positions_reduced', pnl_pct, mode)

    # ========== 統計更新 ==========
    closed_now = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    wins = [t for t in closed_now if t.get('pnl', 0) > 0]
    losses = [t for t in closed_now if t.get('pnl', 0) <= 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed_now)
    wr = len(wins) / len(closed_now) * 100 if closed_now else 0
    trades_data['stats'] = {'total': len(trades_data['trades']), 'wins': len(wins),
                             'losses': len(losses), 'total_pnl': round(total_pnl, 0)}

    tw_open = [t for t in open_now if t.get('market', 'TW') == 'TW']
    us_open = [t for t in open_now if t.get('market') == 'US']

    print('\n' + '=' * 60)
    print(f'📊 Summary')
    print(f'  總交易：{len(trades_data["trades"])} | 開倉：{len(open_now)}(TW:{len(tw_open)}/US:{len(us_open)}) | 閉合：{len(closed_now)}')
    print(f'  勝率：{wr:.0f}% | 勝：{len(wins)} | 負：{len(losses)}')
    print(f'  總損益：NT${total_pnl:+,.0f}')
    if overbought_profit:
        print(f'\n  ⚠️  建議紀律止盈：')
        for sym, pnl, rsi, dist in overbought_profit:
            print(f'    {sym}: {pnl:.1f}% 盈利 RSI={rsi:.0f} 距離目標 {dist:.1f}%')

    save_trades(trades_data)
    print('=' * 60)

    # 發送摘要 Telegram
    summary = (
        f'📊 *Leo 每日檢討 {time.strftime("%Y-%m-%d %H:%M")}*\n'
        f'開倉：{len(open_now)}(TW:{len(tw_open)}/US:{len(us_open)}) | '
        f'閉合：{len(closed_now)} | 勝率：{wr:.0f}%\n'
        f'總損益：NT${total_pnl:+,.0f} | TWII RSI：{twii_rsi:.0f}'
    )
    send_telegram(summary)

# ============================================================
# CLI
# ============================================================
if __name__ == '__main__':
    mode = MODE_AUTO_THINK
    if len(sys.argv) > 1:
        if sys.argv[1] == '--think':
            mode = MODE_FULL_THINK
        elif sys.argv[1] == '--fast':
            mode = MODE_FAST_TRACK
        elif sys.argv[1] == '--status':
            mode = MODE_STATUS

    run_daily_review(mode=mode)