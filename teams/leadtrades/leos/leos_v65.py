"""Leo v6.5 — P1+P2 comprehensive improvements.

P1-1: 大盤 RSI>85 → 降50%倉位
P1-2: 移動停利（進場5%後停損→成本價）
P1-3: 持有10天未達目標→強制減倉50%
P1-4: US停利「目標15% OR $300，取小者」
P2-1: 相對強度過濾（近20日強於大盤>50%）
P2-2: entry_signals 結構化（已有，加強）
P2-3: 加入手續費估算（0.4%/筆）
P2-4: Cooldown 60min→24小時（1440分鐘）
"""
import sys, json, os, time
from pathlib import Path
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
ANALYSIS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_analysis_v65.json'

# === Lessons 查詢系統 ===
LESSONS_DIR = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'memory', 'lessons')
LEDGER_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\experience_ledger.json'


def _query_lessons(sym, max_results=3):
    """
    進場前查詢 Lessons 庫，活化過往失敗/成功經驗
    返回：{'losses': [...], 'wins': [...], 'ledger_entries': [...]}
    """
    result = {'losses': [], 'wins': [], 'ledger_entries': [], 'warnings': []}
    loss_dir = os.path.join(LESSONS_DIR, 'losses')
    win_dir = os.path.join(LESSONS_DIR, 'wins')

    # 讀取 losses
    if os.path.exists(loss_dir):
        for f in sorted(Path(loss_dir).glob(f'{sym}_*.md'), key=lambda x: -x.stat().st_mtime)[:max_results]:
            try:
                result['losses'].append(f.read_text(encoding='utf-8')[:300])
            except: pass

    # 讀取 wins
    if os.path.exists(win_dir):
        for f in sorted(Path(win_dir).glob(f'{sym}_*.md'), key=lambda x: -x.stat().st_mtime)[:max_results]:
            try:
                result['wins'].append(f.read_text(encoding='utf-8')[:300])
            except: pass

    # 讀取 ledger（experience_ledger.json）
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
            for e in ledger:
                if sym in str(e.get('symbol', '')):
                    result['ledger_entries'].append(e)
        except: pass

    # 生成警告文字
    if result['losses']:
        result['warnings'].append(f'⚠️ {sym} 有 {len(result["losses"])} 筆失敗紀錄，進場需格外謹慎')
    if result['ledger_entries']:
        for e in result['ledger_entries']:
            if e.get('win_rate', 100) < 50:
                result['warnings'].append(f'⚠️ {sym} 歷史勝率 {e.get("win_rate", 0):.0f}%，三思而後行')

    return result


def _inject_lessons_warning(sym, rsi):
    """產生 Lessons 活化警告字串，注入進場報告"""
    lr = _query_lessons(sym, max_results=2)
    lines = []
    if lr['losses']:
        lines.append('  [LESSONS] 失敗案例：')
        for l in lr['losses'][:2]:
            lines.append(f'    • {l[:150]}...')
    if lr['warnings']:
        for w in lr['warnings']:
            lines.append(f'  {w}')
    if not lines:
        lines.append(f'  [LESSONS] {sym} 無不良紀錄，系統信心進場')
    return '\n'.join(lines)

# === 核心參數（v2.0 自主學習最優化）===
ENTRY_RSI_MIN = 45
ENTRY_RSI_MAX = 70
EXIT_RSI_MIN = 75
TAKE_PROFIT_PCT = 6
STOP_LOSS_PCT = 10
MAX_POSITION = 100000
COOLDOWN_MIN = 1440          # P2-4: 60分鐘→24小時
HOLD_DAYS_MAX = 45

# P1-4: 美股停利（目標15% OR $300，取小者）
US_MAX_POSITION = 2000
US_TAKE_PROFIT = 300
US_STOP_LOSS = 200
# P2-1: 相對強度門檻（近20日需強於大盤>50%）
RELATIVE_STRENGTH_THRESHOLD = 50  # 百分位排名 > 50

# === P1-1: 大盤過熱降倉 ===
TWII_OVERBOUGHT_RSI = 85
POSITION_SCALE_ON_HOT = 0.5  # RSI>85時，倉位降50%

# === 移動停利（P1-2）===
TRAILING_PROFIT_PCT = 5.0   # 進場+5%後啟動移動停利（停損→成本價）
# P1-3: 持有10天未達目標減倉
FORCE_REDUCE_DAYS = 10
FORCE_REDUCE_PCT = 0.5      # 減倉50%

# === P2-3: 手續費估算 ===
FEE_RATE = 0.004           # 0.4% (0.3%手續費+0.1%證交稅)

# === 動量過濾 ===
MOMENTUM_THRESHOLD = 3.0
MA20_MAX_ABOVE = 20.0

# === 台股科技股池 ===
MONITOR_STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2303': '聯電',
    '2317': '鴻海', '2382': '廣達', '3034': '緯穎',
    '2376': '技嘉', '2379': '瑞昱', '3665': '穎崴',
    '2456': '奇鋐', '3533': '嘉澤', '3532': '昇達科',
    '2371': '華星光', '3443': '創惟', '6717': '大聯大',
}

US_STOCKS = {
    'NVDA': 'NVIDIA', 'AMD': 'AMD', 'QCOM': 'Qualcomm', 'ARM': 'ARM',
    'MU': 'Micron', 'WDC': 'Western Digital', 'STX': 'Seagate',
    'ANET': 'Arista', 'LITE': 'Lumentum', 'COHR': 'Coherent',
    'AMZN': 'Amazon', 'MSFT': 'Microsoft', 'GOOGL': 'Google', 'META': 'Meta',
    'AMAT': 'Applied Mat', 'LRCX': 'Lam Research', 'KLAC': 'KLA', 'SNPS': 'Synopsys', 'ASML': 'ASML',
    'MRVL': 'Marvell', 'AVGO': 'Broadcom',
}

def get_rsi(closes, period=12):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

def get_relative_strength_rank(stock_returns, index_returns):
    """P2-1: 計算股票近20日相對大盤的百分位排名（0-100）"""
    if len(stock_returns) < 20 or len(index_returns) < 20:
        return 50  # 預設中性
    stock_cum = (np.prod(1 + stock_returns[-20:]) - 1) * 100
    index_cum = (np.prod(1 + index_returns[-20:]) - 1) * 100
    rel = stock_cum - index_cum
    # 簡化：>0=強於大盤，<0=弱於大盤；回傳0-100標準化
    normalized = 50 + max(-50, min(50, rel * 5))  # 範圍0-100
    return normalized

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'trades': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_ledger_warning(symbol, market='TW'):
    """活化 Ledger：查詢符號歷史表現，低勝率時發出警告"""
    ledger_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\experience_ledger.json'
    suffix = '.TW' if market == 'TW' else ''
    ledger_sym = f'{symbol}{suffix}' if market == 'TW' else symbol
    
    if not os.path.exists(ledger_path):
        return None
    
    try:
        with open(ledger_path, 'r', encoding='utf-8') as f:
            ledger = json.load(f)
        
        # 找 symbol 或 symbol.TW 匹配的記錄
        for entry in ledger:
            if entry.get('symbol') == ledger_sym or entry.get('symbol') == symbol:
                wr = entry.get('win_rate', 50)
                trades = entry.get('trades', 0)
                if trades >= 5 and wr < 50:
                    return (f'[LEDGER WARNING] {symbol}: '
                            f'历史胜率 {wr:.0f}%（{trades}笔交易），需谨慎评估')
                elif trades >= 5 and wr >= 70:
                    return f'[LEDGER OK] {symbol}: 历史胜率 {wr:.0f}%（{trades}笔），正向参考'
        return None
    except:
        return None

def get_recent_entry(symbol, market='TW', minutes=1440):
    cutoff = time.time() - minutes * 60
    trades_data = load_trades()
    for t in trades_data.get('trades', []):
        if t.get('symbol') == symbol and t.get('market') == market and t.get('status') == 'open':
            try:
                ts = t.get('timestamp', '')
                if ts:
                    entry_time = time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                    if entry_time >= cutoff:
                        return t
            except:
                pass
    return None

def get_twii_rsi():
    """取得TWII RSI（P1-1：大盤過熱判斷）"""
    try:
        twii = yf.Ticker('^TWII').history(period='20d')
        if len(twii) >= 13:
            closes = twii['Close'].dropna().values
            return get_rsi(closes, 12)
    except:
        pass
    return 50  # 預設

def analyze_stock(sym, name, market='TW', index_close=None, idx_returns=None, stock_returns=None, twii_rsi=50):
    try:
        suffix = '.TW' if market == 'TW' else ''
        ticker = yf.Ticker(f'{sym}{suffix}')
        h = ticker.history(period='60d')
        if len(h) < 20:
            return None

        closes = h['Close'].dropna().values
        highs = h['High'].dropna().values
        lows = h['Low'].dropna().values
        cur = float(closes[-1])
        prev = float(closes[-2]) if len(closes) > 1 else cur

        rsi = get_rsi(closes, 12)
        ma20 = get_ma(closes, 20)
        ma60 = get_ma(closes, 60) if len(closes) >= 60 else ma20
        mom5 = get_momentum(closes, 5)
        mom20 = get_momentum(closes, 20)

        pos_ma20 = ((cur - ma20) / ma20 * 100) if ma20 != 0 else 0
        pos_ma60 = ((cur - ma60) / ma60 * 100) if ma60 != 0 else 0

        vol5 = h['Volume'].rolling(5).mean().iloc[-1]
        vol_now = h['Volume'].iloc[-1]
        vol_ratio = (vol_now / vol5) if vol5 > 0 else 1

        # 大盤相對動量
        rel_momentum = mom5
        if index_close:
            idx_ticker = yf.Ticker('^TWII' if market == 'TW' else 'SPY')
            idx_hist = idx_ticker.history(period='5d')
            if not idx_hist.empty and len(idx_hist) >= 2:
                idx_prev = float(idx_hist['Close'].iloc[-2])
                idx_mom = (index_close / idx_prev - 1) * 100 if idx_prev != 0 else 0
                rel_momentum = mom5 - idx_mom

        # P2-1: 相對強度百分位
        rel_strength = get_relative_strength_rank(stock_returns, idx_returns) if (stock_returns is not None and idx_returns is not None) else 50

        score = 0
        signals = []

        rsi_max = 75 if market == 'US' else 70
        if rsi < 40:
            score += 30; signals.append('deep_oversold')
        elif rsi < 50:
            score += 20; signals.append('oversold')
        elif rsi < rsi_max:
            score += 10; signals.append('neutral')
        elif rsi < 80:
            score += 5; signals.append('warm')

        if mom5 > 8:
            score += 15; signals.append('strong_momentum')
        elif mom5 > 4:
            score += 10
        elif mom5 > 0:
            score += 5

        if 0 < pos_ma20 < 10:
            score += 15; signals.append('above_ma20')
        elif -5 < pos_ma20 <= 0:
            score += 10; signals.append('near_ma20_pullback')
        elif pos_ma20 > 15:
            score -= 10

        if pos_ma60 > 0:
            score += 8

        if vol_ratio > 1.5:
            score += 5; signals.append('high_volume')
        elif vol_ratio < 0.5:
            score -= 5

        # P2-1: 相對強度篩選（需 > 50）
        if rel_strength < RELATIVE_STRENGTH_THRESHOLD:
            score -= 15; signals.append('weak_vs_market')

        # P1-1: 大盤過熱降倉
        pos_scale = POSITION_SCALE_ON_HOT if twii_rsi > TWII_OVERBOUGHT_RSI else 1.0

        # P1-4: US停利「目標15% OR $300，取小者」
        if market == 'US':
            price_target_pct = (cur * 1.15 - cur) / cur * 100  # 15%利潤對應的%
            # 轉換為股數：$300 / (15% * price) = 股數
            tp_from_dollar = US_TAKE_PROFIT / (0.15 * cur / 100) if cur > 0 else 0
            tp_from_pct = cur * 1.15
            # 取小者（目標價更低=更容易觸發）
            target = round(min(tp_from_dollar, tp_from_pct), 2)
            stop = round(cur - US_STOP_LOSS / (US_MAX_POSITION / cur), 2)
            max_pos = int(US_MAX_POSITION * pos_scale)
            entry_ratio = '1 unit (~$2000)' if pos_scale == 1.0 else 'scaled (TWII hot)'
        else:
            target = round(cur * 1.15, 2)
            stop = round(cur * 0.90, 2)
            max_pos = int(MAX_POSITION * pos_scale)
            entry_ratio = '20%+20%'

        shares = int(max_pos / cur)

        # P2-3: 手續費估算
        fee_estimate = round(shares * cur * FEE_RATE, 0)

        return {
            'symbol': sym, 'name': name, 'market': market,
            'price': round(cur, 2),
            'prev': round(prev, 2),
            'rsi': round(rsi, 1),
            'rsi_label': 'OB' if rsi > 70 else ('OS' if rsi < 45 else ''),
            'mom5': round(mom5, 2), 'mom20': round(mom20, 2),
            'rel_momentum': round(rel_momentum, 2),
            'rel_strength': round(rel_strength, 1),
            'pos_ma20': round(pos_ma20, 1), 'pos_ma60': round(pos_ma60, 1),
            'ma20': round(ma20, 2), 'ma60': round(ma60, 2),
            'vol_ratio': round(vol_ratio, 1),
            'score': score, 'signals': signals,
            'target': target,
            'stop': stop,
            'max_position': max_pos,
            'position_scale': pos_scale,
            'entry_ratio': entry_ratio,
            'shares': shares,
            'fee_estimate': fee_estimate,
            'twii_rsi': round(twii_rsi, 1),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            # P0: Lessons 活化 — 每次分析自動注入進場警告
            'lessons_warning': _inject_lessons_warning(sym, rsi),
            'lessons_query': _query_lessons(sym, max_results=2),
        }
    except Exception as e:
        return None

def analyze_all():
    results = []

    # TWII RSI（P1-1）
    twii_rsi = get_twii_rsi()
    print(f'  TWII RSI: {twii_rsi:.0f} {"[HOT - 50% position scale]" if twii_rsi > TWII_OVERBOUGHT_RSI else ""}')

    twii_close = None
    spy_close = None
    twii_returns = None
    spy_returns = None
    stock_returns_map = {}

    try:
        twii = yf.Ticker('^TWII').history(period='30d')
        if not twii.empty:
            twii_close = float(twii['Close'].iloc[-1])
            twii_returns = twii['Close'].pct_change().dropna().values
    except:
        pass

    try:
        spy = yf.Ticker('SPY').history(period='30d')
        if not spy.empty:
            spy_close = float(spy['Close'].iloc[-1])
            spy_returns = spy['Close'].pct_change().dropna().values
    except:
        pass

    # TW stocks
    for sym, name in MONITOR_STOCKS.items():
        r = analyze_stock(sym, name, 'TW', twii_close, twii_returns, stock_returns_map.get(sym), twii_rsi)
        if r:
            results.append(r)

    # US stocks
    for sym, name in US_STOCKS.items():
        r = analyze_stock(sym, name, 'US', spy_close, spy_returns, stock_returns_map.get(sym), twii_rsi)
        if r:
            results.append(r)

    results.sort(key=lambda x: x['score'], reverse=True)

    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

def run_cycle():
    print('=' * 60)
    print('Leo v6.5 科技股波段 — P1+P2 增強版')
    print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    print()
    print('[Step 1] 分析科技股（TW + US）...')
    analysis = analyze_all()
    tw_cnt = sum(1 for r in analysis if r['market'] == 'TW')
    us_cnt = sum(1 for r in analysis if r['market'] == 'US')
    print(f'完成: {tw_cnt} 檔台股 + {us_cnt} 檔美股')

    print()
    print('[Step 2] 檢查交易機會...')
    trades_data = load_trades()

    entries, exits, reduces = 0, 0, 0
    current = {(a['symbol'], a['market']): a for a in analysis}

    # === 檢查出场 + P1-2移動停利 + P1-3持有10天減倉 ===
    for t in trades_data.get('trades', []):
        if t.get('status') != 'open':
            continue
        key = (t['symbol'], t.get('market', 'TW'))
        if key not in current:
            continue

        cur = current[key]['price']
        entry = t['entry_price']
        shares = t['shares']
        target = t.get('target_price', entry * 1.15)
        stop = t.get('stop_loss', entry * 0.90)
        rsi = current[key]['rsi']
        pnl_pct = (cur - entry) / entry * 100
        pnl_abs = (cur - entry) * shares

        # 持有天數
        try:
            entry_time = time.mktime(time.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S'))
            days_held = (time.time() - entry_time) / 86400
        except:
            days_held = 0

        reason = None
        reduced = False

        # P1-2: 移動停利（trailing stop）
        # 如果有trailing_stop（已啟動），用更嚴格的停損
        trailing_stop = t.get('trailing_stop', stop)

        if t.get('market') == 'US':
            # P1-4: US停利「目標15% OR $300，取小者」已在target計算
            if pnl_abs >= (target - entry) * shares:
                reason = 'take_profit_15pct_or_300'
            elif pnl_abs <= -200:
                reason = 'stop_loss_us'
            # P1-2: 移動停利 — 如果pnl>5%，停損→成本價
            if pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry  # 成本價
                t['trailing_stop_active'] = True
                print(f'  TRAILING STOP ACTIVATED {t["symbol"]}: stop -> ${entry} (cost basis)')
            elif t.get('trailing_stop_active') and cur <= trailing_stop:
                reason = 'trailing_stop_triggered'
        else:
            # P1-2: TW移動停利
            if pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry
                t['trailing_stop_active'] = True
                print(f'  TRAILING STOP ACTIVATED {t["symbol"]}: stop -> ${entry} (cost basis)')
            elif t.get('trailing_stop_active') and cur <= trailing_stop:
                reason = 'trailing_stop_triggered'
            elif cur >= target:
                reason = 'take_profit'
            elif cur <= stop:
                reason = 'stop_loss'
            elif rsi > 80:
                reason = 'overbought_exit'

            # P1-3: 持有10天未達目標，強制減倉50%
            if days_held >= FORCE_REDUCE_DAYS and pnl_pct < 5 and not t.get('reduced_once'):
                new_shares = int(shares * FORCE_REDUCE_PCT)
                if new_shares >= 1 and new_shares < shares:
                    closed_pnl = (cur - entry) * (shares - new_shares)
                    t['shares'] = new_shares
                    t['amount'] = round(new_shares * cur, 0)
                    t['reduced_once'] = True
                    t['exit_reason'] = f'force_reduce_day10_pnl{pnl_pct:.1f}pct'
                    # 記錄減倉後保留口的新trailing
                    if t.get('trailing_stop_active'):
                        t['trailing_stop'] = max(entry, t.get('trailing_stop', entry))
                    reduces += 1
                    print(f'  REDUCED {t["symbol"]}: {shares}->{new_shares} shares (day10, pnl={pnl_pct:+.1f}%)')
                    reduced = True

        if reason and not reduced:
            t['status'] = 'closed'
            t['exit_price'] = cur
            t['exit_reason'] = reason
            t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            t['pnl'] = round((cur - entry) * shares, 0)
            t['pnl_pct'] = round(pnl_pct, 2)
            exits += 1
            mkt = t.get('market', 'TW')
            print(f'  EXIT {t["symbol"]}({mkt}): {reason} -> ${cur} ({pnl_pct:+.1f}%)')

    # === 評估進場 ===
    for stock in analysis:
        sym = stock['symbol']
        mkt = stock['market']
        rsi = stock['rsi']
        score = stock['score']
        pos_ma20 = stock['pos_ma20']
        rel_mom = stock['rel_momentum']
        rel_strength = stock.get('rel_strength', 50)

        # P2-1: 相對強度過濾（需 > 50）
        if rel_strength < RELATIVE_STRENGTH_THRESHOLD:
            continue
        if rsi < ENTRY_RSI_MIN or rsi > ENTRY_RSI_MAX:
            continue
        if score < 30:
            continue
        if pos_ma20 > MA20_MAX_ABOVE:
            continue
        if rel_mom < -5:
            continue
        if get_recent_entry(sym, mkt, COOLDOWN_MIN):
            continue

        # 活化 Ledger 警告（P2-0: 經驗傳承）
        ledger_warn = check_ledger_warning(sym, mkt)
        if ledger_warn:
            print(f'  {ledger_warn}')

        shares = stock['shares']
        if shares < 1:
            continue

        existing = [t for t in trades_data['trades']
                    if t.get('symbol') == sym and t.get('market') == mkt and t.get('status') == 'open']
        if len(existing) >= 3:
            continue

        # P1-1: 大盤過熱提示
        pos_note = ' (HALVED - TWII hot)' if stock['position_scale'] < 1.0 else ''

        trade = {
            'symbol': sym,
            'name': stock['name'],
            'market': mkt,
            'entry_price': stock['price'],
            'shares': shares,
            'amount': round(shares * stock['price'], 0),
            'entry_rsi': rsi,
            'entry_score': score,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'target_price': stock['target'],
            'stop_loss': stock['stop'],
            'trailing_stop': stock['stop'],  # P1-2: 初始trailing_stop
            'trailing_stop_active': False,
            'status': 'open',
            'trade_id': f'LEO_{mkt[0]}{sym}_{time.strftime("%Y%m%d%H%M%S")}',
            'entry_signals': stock['signals'],
            'fee_estimate': stock['fee_estimate'],
            'rel_strength': stock.get('rel_strength', 50),
            'twii_rsi': stock.get('twii_rsi', 50),
            'position_scale': stock['position_scale'],
        }
        trades_data['trades'].append(trade)
        entries += 1

        # P0-3: Entry 專家委員會審查（Lessons活化 + 三方投票）
        from tina_think import run_expert_committee, log_committee_prediction, _query_lessons as tina_query_lessons
        entry_committee = run_expert_committee(stock, open_pos)
        log_committee_prediction(entry_committee, stock, entry_committee['decision'])
        if entry_committee['decision'] == 'REJECT':
            trade['status'] = 'rejected_by_committee'
            trade['rejected_reason'] = f"Committee REJECT: {entry_committee['risk']['verdict']}"
            print(f'  !! Committee REJECTED {sym} — {entry_committee["risk"]["summary"]}')
        elif entry_committee['decision'] == 'CAUTION':
            trade['committee_caution'] = True
            trade['committee_score'] = entry_committee['total_score']
            print(f'  !  Committee CAUTION ({entry_committee["total_score"]:.0f}分) — 小部位進場')
        print(f'  ENTRY {sym}({mkt}) {stock["name"]}: ${stock["price"]} RSI={rsi} Score={score}{pos_note}')
        # P0: Lessons 活化報告注入
        lw = stock.get('lessons_warning', '')
        if lw and lw != f'  [LESSONS] {sym} 無不良紀錄，系統信心進場':
            for line in lw.split('\n'):
                if line.strip():
                    print(f'    {line.strip()}')
        print(f'    -> Target: ${stock["target"]} | Stop: ${stock["stop"]} | RelStr: {rel_strength:.0f}')

    save_trades(trades_data)

    # Step 3: 摘要
    print()
    closed = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    open_pos = [t for t in trades_data['trades'] if t.get('status') == 'open']
    wins = [t for t in closed if t.get('pnl', 0) > 0]
    losses = [t for t in closed if t.get('pnl', 0) < 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed)
    wr = len(wins) / len(closed) * 100 if closed else 0

    tw_open = [t for t in open_pos if t.get('market', 'TW') == 'TW']
    us_open = [t for t in open_pos if t.get('market') == 'US']

    print(f'[Step 3] Summary')
    print(f'  Total: {len(trades_data["trades"])} | Open: {len(open_pos)}(TW:{len(tw_open)}/US:{len(us_open)}) | Closed: {len(closed)}')
    print(f'  WR: {wr:.0f}% | Wins: {len(wins)} | Losses: {len(losses)}')
    print(f'  Total PnL: NT${total_pnl:+,.0f}')
    print(f'  Entries: {entries} | Exits: {exits} | Reduces: {reduces}')

    if open_pos:
        print()
        print('  Open positions:')
        for t in open_pos:
            key = (t['symbol'], t.get('market', 'TW'))
            cur = current.get(key, {}).get('price', '?')
            if cur != '?' and isinstance(cur, (int, float)):
                entry = t['entry_price']
                pnl_pct_val = round((cur - entry) / entry * 100 - FEE_RATE * 200, 2)
                t['current_price'] = cur
                t['pnl_pct'] = pnl_pct_val
            pnl_pct = t.get('pnl_pct', 0)
            trailing = '[TRAILING]' if t.get('trailing_stop_active') else ''
            print(f'    {t["symbol"]}({t.get("market","TW")}): ${t["entry_price"]} -> ${cur} ({pnl_pct:+.1f}%) {trailing}')

    print()
    print('Done')
    return trades_data

if __name__ == '__main__':
    run_cycle()
