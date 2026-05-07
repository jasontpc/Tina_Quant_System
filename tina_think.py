"""Tina Think Engine - 慢思考實戰化 v1.0

Think → Report → Wait → Act → Log

三種模式:
- Full Think: 手動觸發 → 報告→等確認→執行
- Auto Think: Cron 自動化 → 報告+執行(事後補日誌)
- Fast Track: 緊急市場警示 → 直接行動(事後補報告)

專家委員會:
- 量化分析師(35%):RSI、動量、MA 結構
- 資深開發者(35%):策略穩定性、參數合理性
- 風控長(30%):最大虧損、部位集中度
"""
import sys, os, json, time, yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = '1616824689'

# === 專家權重 ===
EXPERT_WEIGHTS = {
    'quant': 0.35,   # 量化分析師
    'dev': 0.35,     # 開發者
    'risk': 0.30,    # 風控長
}

# === Lessons 查詢系統 ===
LESSONS_DIR = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'memory', 'lessons')
LEDGER_FILE = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'Tina_Quant_System', 'data', 'experience_ledger.json')


def _query_lessons(sym, max_results=2):
    """
    進場前查詢 Lessons 庫，活化過往失敗/成功經驗
    返回：{'losses': [...], 'wins': [...], 'ledger_entries': [...], 'warnings': [...]}
    """
    from pathlib import Path
    result = {'losses': [], 'wins': [], 'ledger_entries': [], 'warnings': []}
    loss_dir = os.path.join(LESSONS_DIR, 'losses')
    win_dir = os.path.join(LESSONS_DIR, 'wins')

    if os.path.exists(loss_dir):
        for f in sorted(Path(loss_dir).glob(f'{sym}_*.md'), key=lambda x: -x.stat().st_mtime)[:max_results]:
            try:
                result['losses'].append(f.read_text(encoding='utf-8')[:300])
            except: pass

    if os.path.exists(win_dir):
        for f in sorted(Path(win_dir).glob(f'{sym}_*.md'), key=lambda x: -x.stat().st_mtime)[:max_results]:
            try:
                result['wins'].append(f.read_text(encoding='utf-8')[:300])
            except: pass

    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
            for e in ledger:
                if sym in str(e.get('symbol', '')):
                    result['ledger_entries'].append(e)
        except: pass

    if result['losses']:
        result['warnings'].append(f'⚠️ {sym} 有 {len(result["losses"])} 筆失敗紀錄')
    if result['ledger_entries']:
        for e in result['ledger_entries']:
            if e.get('win_rate', 100) < 50:
                result['warnings'].append(f'⚠️ {sym} 歷史勝率 {e.get("win_rate",0):.0f}%')

    return result


def log_committee_prediction(committee, stock_data, decision, actual_result=None):
    """
    委員會預測日誌 — 記錄委員會預測，用於 PDCA 反饋
    actual_result 在事後填入（win/loss/breakeven）
    """
    log_dir = os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace', 'memory', 'portfolio', 'decisions')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'committee_pred.json')

    entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': stock_data.get('symbol', ''),
        'market': stock_data.get('market', 'TW'),
        'decision': decision,
        'total_score': committee.get('total_score', 0),
        'quant_predicted': committee.get('quant', {}).get('verdict', ''),
        'dev_predicted': committee.get('dev', {}).get('verdict', ''),
        'risk_predicted': committee.get('risk', {}).get('verdict', ''),
        'twii_rsi': committee.get('twii_rsi', 50),
        'rsi': stock_data.get('rsi', 50),
        'entry_price': stock_data.get('price', 0),
        'actual_result': actual_result,  # filled later
    }

    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(entry)
        logs = logs[-500:]  # keep last 500
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[COMMITTEE LOG] Failed: {e}')

# === 風控限制 ===
MAX_POSITION_CONCENTRATION = 3  # 每檔股票最多3口
MAX_TOTAL_RISK = 0.40           # 總部位上限 40%
MAX_SINGLE_LOSS = -0.08          # 單筆最大虧損 -8%
TWII_HOT_RSI = 85               # 大盤過熱門檻

# === 模式切換 ===
MODE_FULL_THINK = 'full_think'   # 手動觸發:報告→等確認→執行
MODE_AUTO_THINK = 'auto_think'   # Cron自動化:報告+執行(事後補日誌)
MODE_FAST_TRACK = 'fast_track'   # 緊急警示:直接行動(事後補報告)

# ========================
# Telegram 發送
# ========================
def send_telegram(text):
    """發送 Telegram 訊息"""
    import urllib.request, urllib.parse

    if not TELEGRAM_TOKEN:
        print(f'[TG] {text[:200]}...')
        return True

    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
        return True
    except Exception as e:
        print(f'Telegram send failed: {e}')
        return False

def send_telegram_photo(image_path, caption=''):
    """發送圖片"""
    import urllib.request

    if not TELEGRAM_TOKEN or not os.path.exists(image_path):
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
    with open(image_path, 'rb') as f:
        try:
            import multipart
            fields = [('chat_id', CHAT_ID), ('caption', caption)]
            files = [('photo', 'chart.png', f.read())]
            data, content_type = multipart.encode(fields, files)
            req = urllib.request.Request(url, data=data, headers={'Content-Type': content_type})
            with urllib.request.urlopen(req, timeout=30):
                pass
            return True
        except Exception as e:
            print(f'Photo send failed: {e}')
            return False

# ========================
# 專家委員會分析
# ========================
def get_twii_data():
    """取得 TWII 數據"""
    try:
        twii = yf.Ticker('^TWII').history(period='20d')
        if len(twii) >= 13:
            closes = twii['Close'].dropna().values
            rsi = get_rsi(closes, 12)
            mom5 = get_momentum(closes, 5)
            return {'rsi': rsi, 'mom5': mom5, 'close': float(closes[-1])}
    except:
        pass
    return {'rsi': 50, 'mom5': 0, 'close': 0}

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

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

def expert_quant(data):
    """專家一:量化分析師(35%)- 技術面評估"""
    signals = []
    score = 0

    # RSI 評估
    rsi = data.get('rsi', 50)
    if rsi < 40:
        score += 30; signals.append('RSI 深度超賣')
    elif rsi < 50:
        score += 20; signals.append('RSI 超賣')
    elif rsi < 65:
        score += 10; signals.append('RSI 中性偏多')
    else:
        score -= 10; signals.append('RSI 偏高')

    # 動量評估
    mom5 = data.get('mom5', 0)
    if mom5 > 5:
        score += 20; signals.append('5日動量強')
    elif mom5 > 0:
        score += 10; signals.append('5日動量正')
    else:
        score -= 10; signals.append('5日動量負')

    # MA20 位置
    pos_ma20 = data.get('pos_ma20', 0)
    if 0 < pos_ma20 < 10:
        score += 15; signals.append('價格站上 MA20')
    elif -5 < pos_ma20 <= 0:
        score += 10; signals.append('價格回測 MA20 支撐')
    elif pos_ma20 > 15:
        score -= 10; signals.append('MA20 偏離過大')

    return {
        'expert': 'quant',
        'weight': EXPERT_WEIGHTS['quant'],
        'score': score,
        'signals': signals,
        'verdict': 'BUY' if score >= 50 else ('SELL' if score <= 20 else 'HOLD'),
        'summary': f'技術面評分:{score}分 {"|".join(signals[:3])}'
    }

def expert_dev(data):
    """專家二:資深開發者(35%)- 策略穩定性"""
    signals = []
    score = 50

    # 進場合理性
    rsi = data.get('rsi', 50)
    if 45 <= rsi <= 70:
        score += 20; signals.append('RSI 在理想進場區間 45-70')
    elif 40 <= rsi < 45:
        score += 10; signals.append('RSI 偏低但合理')
    else:
        score -= 15; signals.append(f'RSI {rsi} 不在最佳進場區間')

    # 動量穩定性
    mom5 = data.get('mom5', 0)
    mom20 = data.get('mom20', 0)
    if mom5 > 0 and mom20 > 0:
        score += 15; signals.append('動量結構健康(短>0,長>0)')
    elif mom5 < 0 and mom20 < 0:
        score -= 15; signals.append('動量結構偏弱')
    else:
        score += 5; signals.append('動量震盪')

    # 市場環境
    twii_hot = data.get('twii_hot', False)
    if twii_hot:
        score -= 10; signals.append('⚠️ TWII 過熱,降倉50%')

    return {
        'expert': 'dev',
        'weight': EXPERT_WEIGHTS['dev'],
        'score': score,
        'signals': signals,
        'verdict': 'BUY' if score >= 55 else ('SELL' if score <= 25 else 'HOLD'),
        'summary': f'策略評分:{score}分 {"|".join(signals[:3])}'
    }

def expert_risk(data):
    """專家三：風控長（30%）— 風險評估（Lessons 活化版）"""
    signals = []
    score = 50

    # P0: Lessons 活化 — 有失敗紀錄的股票額外扣分
    sym = data.get('symbol', '')
    lr = _query_lessons(sym, max_results=2)
    if lr['losses']:
        score -= 15
        signals.append(f'!! {sym} 有 {len(lr["losses"])} 筆失敗教訓')
        data['lesson_warning'] = True
    if lr['ledger_entries']:
        for e in lr['ledger_entries']:
            if e.get('win_rate', 100) < 50:
                score -= 10
                signals.append(f'!! {sym} 歷史勝率 {e.get("win_rate",0):.0f}%，三思')

    # 大盤環境
    twii_rsi = data.get('twii_rsi', 50)
    if twii_rsi > TWII_HOT_RSI:
        score -= 20; signals.append(f'!! 大盤 RSI {twii_rsi:.0f} 過熱')
    elif twii_rsi > 70:
        score -= 10; signals.append(f'大盤 RSI {twii_rsi:.0f} 偏高')

    # 部位集中度
    pos_count = data.get('positions_same_stock', 0)
    if pos_count >= 3:
        score -= 25; signals.append(f'XX {data.get("symbol")} 已有{pos_count}口，達上限')
    elif pos_count == 2:
        score -= 10; signals.append(f'! {data.get("symbol")} 已有{pos_count}口')
    else:
        score += 10; signals.append('部位空間充足')

    # 單筆風險
    loss_pct = data.get('current_loss_pct', 0)
    if loss_pct <= -5:
        score -= 15; signals.append(f'當前虧損 {loss_pct:.1f}%，注意')

    return {
        'expert': 'risk',
        'weight': EXPERT_WEIGHTS['risk'],
        'score': score,
        'signals': signals,
        'verdict': 'BUY' if score >= 45 else ('SELL' if score <= 20 else 'HOLD'),
        'summary': f'風控評分：{score}分 {"|".join(signals[:3])}'
    }

def run_expert_committee(stock_data, positions_data):
    """執行專家委員會"""
    twii = get_twii_data()
    twii_hot = twii['rsi'] > TWII_HOT_RSI

    # 合併數據
    data = {
        'rsi': stock_data.get('rsi', 50),
        'mom5': stock_data.get('mom5', 0),
        'mom20': stock_data.get('mom20', 0),
        'pos_ma20': stock_data.get('pos_ma20', 0),
        'twii_rsi': twii['rsi'],
        'twii_hot': twii_hot,
        'symbol': stock_data.get('symbol', ''),
        'positions_same_stock': len([
            t for t in positions_data
            if t.get('symbol') == stock_data.get('symbol')
            and t.get('status') == 'open'
        ]),
        'current_loss_pct': stock_data.get('pnl_pct', 0),
    }

    q = expert_quant(data)
    d = expert_dev(data)
    r = expert_risk(data)

    # 加權總分
    total_score = (
        q['score'] * q['weight'] +
        d['score'] * d['weight'] +
        r['score'] * r['weight']
    )

    # 委員會決定
    verdicts = [q['verdict'], d['verdict'], r['verdict']]
    buy_count = verdicts.count('BUY')
    hold_count = verdicts.count('HOLD')
    sell_count = verdicts.count('SELL')

    if buy_count >= 2:
        decision = 'APPROVE'
    elif hold_count >= 2:
        decision = 'CAUTION'
    else:
        decision = 'REJECT'

    return {
        'quant': q,
        'dev': d,
        'risk': r,
        'total_score': round(total_score, 1),
        'decision': decision,
        'twii_rsi': round(twii['rsi'], 1),
        'twii_hot': twii_hot,
    }

# ========================
# 思考報告生成
# ========================
def generate_thinking_report(symbol, name, market, stock_data, positions_data, mode):
    """生成完整的慢思考報告"""

    committee = run_expert_committee(stock_data, positions_data)
    pos_scale = 0.5 if committee['twii_hot'] else 1.0

    report_lines = [
        '🧠 *Leo 慢思考報告*',
        '=' * 40,
        f'📌 *{symbol} {name}*({market})',
        f'⏰ {time.strftime("%Y-%m-%d %H:%M")}',
        '',
        '📊 *市場環境*',
        f'  TWII RSI: `{committee["twii_rsi"]}` {"🔥 過熱" if committee["twii_hot"] else "✅ 正常"}',
        f'  部位調整: {"×0.5(降50%)" if pos_scale < 1 else "×1.0(全倉)"}',
        '',
        '🔍 *專家委員會*',
        '',
        f'  📈 量化分析師(35%):{committee["quant"]["verdict"]}',
        f'     {committee["quant"]["summary"]}',
        '',
        f'  ⚙️ 資深開發者(35%):{committee["dev"]["verdict"]}',
        f'     {committee["dev"]["summary"]}',
        '',
        f'  🛡️ 風控長(30%):{committee["risk"]["verdict"]}',
        f'     {committee["risk"]["summary"]}',
        '',
        f'  🔗 *加權總分:{committee["total_score"]}*',
        '',
        '🏛️ *委員會決定:{decision}*'.format(**committee),
        '',
    ]

    if committee['decision'] == 'APPROVE':
        action = '✅ 可進場(專家委員會通過)'
        entry = stock_data.get('price', 0)
        target = stock_data.get('target', entry * 1.15)
        stop = stock_data.get('stop', entry * 0.90)
        shares = stock_data.get('shares', 0)
        pnl_note = f'目標 {target:.0f} / 停損 {stop:.0f}'
    elif committee['decision'] == 'CAUTION':
        action = '⚠️ 謹慎進場(建議觀望或小倉位)'
        entry = stock_data.get('price', 0)
        target = stock_data.get('target', entry * 1.15)
        stop = stock_data.get('stop', entry * 0.90)
        shares = int(stock_data.get('shares', 0) * 0.5)
        pnl_note = f'小倉位試單:{shares}股'
    else:
        action = '❌ 否決(風控不通過)'
        entry = target = stop = shares = 0
        pnl_note = '不建議進場'

    report_lines.extend([
        action,
        '',
        f'💡 *建議:{pnl_note}*',
        '',
        f'`RSI {stock_data.get("rsi", 0):.0f} | Score {stock_data.get("score", 0)} | 動量 {stock_data.get("mom5", 0):+.1f}%`',
        '',
    ])

    # 模式提醒
    if mode == MODE_FULL_THINK:
        report_lines.append('🔔 *等待 Jo 回應中...(60秒)*')
        report_lines.append('回覆 `confirm` 確認執行 / `reject` 否決')
    elif mode == MODE_AUTO_THINK:
        report_lines.append('🤖 [Auto Think] 自動執行中,事後補日誌')
    else:
        report_lines.append('⚡ [Fast Track] 緊急模式,直接執行')

    return '\n'.join(report_lines), committee

# ========================
# 決策日誌寫入
# ========================
def log_decision(symbol, name, market, decision, committee, mode, result='pending'):
    """寫入決策日誌"""
    DECISION_LOG = os.path.expanduser('~/.openclaw/workspace/memory/decision_log.md')

    timestamp = time.strftime('%Y-%m-%d %H:%M')

    entry = f"""
### [{timestamp}] 決策:{symbol} {name}({market})

**模式:** {mode}
**委員會決定:** {decision}
**加權總分:** {committee['total_score']}

**專家觀點:**
- 量化分析師:{committee['quant']['verdict']}({committee['quant']['score']}分)
- 資深開發者:{committee['dev']['verdict']}({committee['dev']['score']}分)
- 風控長:{committee['risk']['verdict']}({committee['risk']['score']}分)

**結果:** {result}

---
"""
    try:
        with open(DECISION_LOG, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception as e:
        print(f'Failed to write decision log: {e}')

    # 同時寫入 portfolio/decisions/
    decision_file = os.path.expanduser(f'~/.openclaw/workspace/memory/portfolio/decisions/{symbol}_{time.strftime("%Y%m%d%H%M%S")}.md')
    try:
        os.makedirs(os.path.dirname(decision_file), exist_ok=True)
        with open(decision_file, 'w', encoding='utf-8') as f:
            f.write(entry)
    except:
        pass

# ========================
# 主執行流程
# ========================
def think_and_execute(symbol, name, market, stock_data, positions_data, mode, execute_callback=None):
    """
    慢思考主流程

    Args:
        symbol: 股票代碼
        name: 名稱
        market: TW/US
        stock_data: 分析數據(rsi, score, mom5, price, target, stop, shares...)
        positions_data: 現有倉位列表
        mode: MODE_FULL_THINK / MODE_AUTO_THINK / MODE_FAST_TRACK
        execute_callback: 實際執行回調函數
    """
    # Step 1: 生成思考報告
    report, committee = generate_thinking_report(symbol, name, market, stock_data, positions_data, mode)

    # Step 2: 發送報告
    send_telegram(report)

    # Step 3: 根據模式處理
    if mode == MODE_FULL_THINK:
        # 等待回應(60秒)
        # 在 Cron 環境無法真正等待,這裡改為發送後由 Jo 回應觸發
        log_decision(symbol, name, market, committee['decision'], committee, mode, '等待確認')
        return {'status': 'waiting', 'report': report, 'committee': committee}

    elif mode == MODE_AUTO_THINK:
        # 自動執行
        if committee['decision'] == 'APPROVE':
            if execute_callback:
                result = execute_callback(symbol, name, market, stock_data)
            else:
                result = 'executed_auto'
            log_decision(symbol, name, market, committee['decision'], committee, mode, result)
            send_telegram(f'✅ [{symbol}] 已自動執行 | 結果:{result}')
        elif committee['decision'] == 'CAUTION':
            # 謹慎模式:小倉位
            stock_data['shares'] = int(stock_data.get('shares', 0) * 0.5)
            if execute_callback:
                result = execute_callback(symbol, name, market, stock_data)
            else:
                result = 'executed_caution'
            log_decision(symbol, name, market, committee['decision'], committee, mode, result)
            send_telegram(f'⚠️ [{symbol}] 謹慎執行(小倉位) | 結果:{result}')
        else:
            log_decision(symbol, name, market, committee['decision'], committee, mode, 'rejected_by_committee')
            send_telegram(f'❌ [{symbol}] 否決 | {committee["risk"]["summary"]}')
        return {'status': 'done', 'result': result, 'committee': committee}

    elif mode == MODE_FAST_TRACK:
        # 緊急模式:直接執行,事後補報告
        if execute_callback:
            result = execute_callback(symbol, name, market, stock_data)
        else:
            result = 'executed_fast'
        log_decision(symbol, name, market, 'FAST_TRACK', committee, mode, result)
        send_telegram(f'⚡ [{symbol}] Fast Track 執行 | 結果:{result}')
        return {'status': 'done', 'result': result, 'committee': committee}

# ========================
# 輔助:從 Leo 分析報告讀取股票數據
# ========================
def load_analysis_for_symbol(symbol, market='TW'):
    """從 leos_analysis_v65.json 讀取單一股票分析數據"""
    analysis_file = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_analysis_v65.json'
    if not os.path.exists(analysis_file):
        return None
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        for r in results:
            if r.get('symbol') == symbol and r.get('market') == market:
                return r
    except:
        pass
    return None

def load_positions():
    """讀取 Leo 當前倉位"""
    trades_file = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
    if not os.path.exists(trades_file):
        return []
    try:
        with open(trades_file, 'r', encoding='utf-8') as f:
            td = json.load(f)
        return td.get('trades', [])
    except:
        return []

# ========================
# CLI 介面
# ========================
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python tina_think.py <symbol> <mode>')
        print('  mode: full_think | auto_think | fast_track')
        sys.exit(1)

    symbol = sys.argv[1]
    mode = sys.argv[2]

    # 根據 symbol 找 market
    suffix = '.TW' if symbol.isdigit() else ''
    market = 'TW' if suffix else 'US'
    full_sym = f'{symbol}{suffix}'

    name_map_tw = {
        '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
        '2382': '廣達', '3034': '緯穎', '2376': '技嘉',
        '2379': '瑞昱', '3665': '穎崴',
    }
    name_map_us = {
        'NVDA': 'NVIDIA', 'AMD': 'AMD', 'MSFT': 'Microsoft',
        'AMZN': 'Amazon', 'GOOGL': 'Google', 'META': 'Meta',
    }
    name = name_map_tw.get(symbol, name_map_us.get(symbol, symbol))

    print(f'Thinking about {symbol} ({name}) in {mode} mode...')

    # 載入分析數據
    stock_data = load_analysis_for_symbol(symbol, market)
    positions = load_positions()

    if not stock_data:
        print(f'No analysis data for {symbol}')
        sys.exit(1)

    # 執行慢思考
    result = think_and_execute(symbol, name, market, stock_data, positions, mode)
    print(f'Result: {result["status"]}')