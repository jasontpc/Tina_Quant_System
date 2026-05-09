# -*- coding: utf-8 -*-
"""
Tina Health Check v2 — 智慧健檢系統
===================================
每日自動執行（07:00 & 22:00）
結合記憶系統（short_term / long_term / lessons / patterns）

檢查維度：
1. 系統健康（DB / Cron / 腳本）
2. 市場環境（TWII RSI / VIX / 法人流向）
3. 持倉健檢（持有天數 / 停損觸發 / RSI現值）
4. 策略一致性（今日 vs 昨日 vs 上週）
5. 記憶系統健康（蒸餾記錄 / Lesson 沉積）

輸出：stores/short_term/health_check_v2_report.json
"""
import sys, json, os, time, sqlite3
from datetime import datetime, timedelta
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(BASE, 'data')
STORES_DIR = os.path.join(BASE, 'stores')
SHORT_TERM = os.path.join(STORES_DIR, 'short_term')
LONG_TERM = os.path.join(STORES_DIR, 'long_term')
POSITIONS_FILE = os.path.join(DATA_DIR, 'position_tracker.json')
OUTPUT = os.path.join(SHORT_TERM, 'health_check_v2_report.json')

# FinMind
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'
FINMIND_BASE = 'https://api.finmindtrade.com/api/v4/data'

# 門檻
RSI_NEW_BAN = 75
RSI_REDUCE_25 = 80
RSI_REDUCE_50 = 85
HOLD_WARN = 20
HOLD_REVIEW = 25
HOLD_FORCE = 30

def get_rsi(c, p=12):
    if len(c) < p + 1: return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

def get_db_health():
    """檢查所有 DB 健康狀態"""
    db_dir = os.path.join(BASE, 'data')
    results = []
    if not os.path.exists(db_dir):
        return {'status': 'ERROR', 'details': 'data dir not found'}
    for f in os.listdir(db_dir):
        if f.endswith('.db'):
            path = os.path.join(db_dir, f)
            try:
                size = os.path.getsize(path)
                conn = sqlite3.connect(path)
                c = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                results.append({
                    'file': f,
                    'size_mb': round(size / 1024 / 1024, 1),
                    'status': 'OK' if c[0] == 'ok' else 'WARNING'
                })
            except Exception as e:
                results.append({'file': f, 'size_mb': 0, 'status': f'ERROR: {e}'})
    return {'status': 'OK' if all(r['status'] == 'OK' for r in results) else 'WARNING', 'details': results}

def get_cron_health():
    """檢查 Cron jobs 狀態 — 透過 openclaw cron list"""
    import subprocess
    try:
        result = subprocess.run(['openclaw', 'cron', 'list', '--include-disabled'], 
                                  capture_output=True, text=True, timeout=15)
        output = result.stdout
        if 'error' in output.lower() or result.returncode != 0:
            return {'status': 'UNKNOWN', 'details': '無法讀取cron狀態'}
        lines = output.strip().split('\n')
        error_count = sum(1 for l in lines if 'error' in l.lower())
        return {'status': 'WARNING' if error_count > 0 else 'OK', 'total_lines': len(lines), 'errors': error_count}
    except:
        return {'status': 'UNKNOWN', 'details': 'timeout reading cron'}

def get_twii_data():
    """抓 TWII 數據"""
    try:
        h = yf.Ticker('^TWII').history(period='60d')
        if h.empty: return None
        c = h['Close'].values
        rsi = get_rsi(c, 14)
        ma20 = float(np.mean(c[-20:])) if len(c) >= 20 else c[-1]
        ma60 = float(np.mean(c[-60:])) if len(c) >= 60 else c[-1]
        return {
            'rsi': round(float(rsi), 1),
            'price': round(float(c[-1]), 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'ma_signal': 'bullish' if ma20 > ma60 else 'bearish' if ma20 < ma60 else 'neutral'
        }
    except:
        return None

def get_vix():
    try:
        h = yf.Ticker('^VIX').history(period='20d')
        return round(float(h['Close'].values[-1]), 2) if not h.empty else None
    except:
        return None

def get_institutional_flow():
    yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    three_days_ago = (datetime.today() - timedelta(days=4)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': 'TWSE', 'start_date': three_days_ago, 'end_date': yesterday, 'token': FINMIND_TOKEN,
    }
    try:
        import urllib.request, urllib.parse
        url = FINMIND_BASE + '?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success'):
                recent = data['data'][-3:] if len(data['data']) >= 3 else data['data']
                net = sum(d.get('buy', 0) - d.get('sell', 0) for d in recent)
                return {'net': net, 'signal': 'bullish' if net > 0 else 'bearish' if net < 0 else 'neutral'}
    except:
        pass
    return {'net': 0, 'signal': 'unknown'}

def get_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
            if isinstance(d, dict): return d.get('positions', [])
            return d
    return []

def get_memory_stats():
    """檢查記憶系統健康"""
    stats = {}
    # short_term count
    if os.path.exists(SHORT_TERM):
        st_files = [f for f in os.listdir(SHORT_TERM) if f.endswith('.json')]
        stats['short_term_files'] = len(st_files)
    else:
        stats['short_term_files'] = 0
    # long_term
    lt_files = []
    for fname in ['lessons.json', 'patterns.json', 'frameworks.json']:
        path = os.path.join(LONG_TERM, fname)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                lt_files.append({'file': fname, 'count': len(d) if isinstance(d, (list, dict)) else 0})
    stats['long_term'] = lt_files
    # distillation log
    dist_log = os.path.join(STORES_DIR, 'distillation_log.json')
    if os.path.exists(dist_log):
        try:
            with open(dist_log, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, list) and len(d) > 0:
                stats['last_distillation'] = d[-1]
            elif isinstance(d, dict):
                stats['last_distillation'] = d.get('entries', [{}])[-1] if d.get('entries') else None
            else:
                stats['last_distillation'] = None
        except:
            stats['last_distillation'] = None
    else:
        stats['last_distillation'] = None
    return stats

def get_market_sentiment(twii_data, vix, inst_flow):
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
    if inst_flow and inst_flow['signal'] == 'bullish': score += 10
    elif inst_flow and inst_flow['signal'] == 'bearish': score -= 10
    return max(0, min(100, score))

# ═══ 主程式 ═══
print('===========================================')
print(' Tina Health Check v2 — 智慧健檢')
print(f' Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('===========================================')

report = {'timestamp': datetime.now().isoformat(), 'sections': {}}

# 1. System Health
print('\n[1/5] 系統健康...')
db_health = get_db_health()
cron_health = get_cron_health()
report['sections']['system'] = {'db': db_health, 'cron': cron_health}
print(f'  DB: {db_health["status"]} | Cron: {cron_health["status"]}')

# 2. Market Environment
print('\n[2/5] 市場環境...')
twii = get_twii_data()
vix = get_vix()
inst_flow = get_institutional_flow()
sentiment = get_market_sentiment(twii, vix, inst_flow)
report['sections']['market'] = {
    'twii': twii,
    'vix': vix,
    'inst_flow': inst_flow,
    'sentiment': sentiment,
}
print(f'  TWII RSI={twii["rsi"] if twii else "N/A"} | VIX={vix} | Inst={inst_flow["signal"]} | Sentiment={sentiment}/100')

# 3. Position Health
print('\n[3/5] 持倉健檢...')
positions = get_positions()
pos_report = []
for p in positions:
    sym = p.get('symbol', '?')
    days = p.get('days_held', 0)
    cost = p.get('cost', 0)
    current = p.get('current_price', cost)
    target = p.get('target', 0)
    stop = p.get('stop_loss', 0)
    pnl_pct = p.get('pnl_pct', 0)

    # RSI 現值
    try:
        ticker = sym if '.' in sym else (f'{sym}.TW' if sym.isdigit() or sym.startswith('00') else sym)
        h = yf.Ticker(ticker).history(period='20d')
        rsi = round(get_rsi(h['Close'].values), 1) if not h.empty else 50.0
    except:
        rsi = 50.0

    # 距離
    dist_stop = (current - stop) / current * 100 if stop > 0 else 999
    dist_target = (target - current) / current * 100 if target > 0 else 999

    # 狀態
    if days >= HOLD_FORCE:
        status = '🚨 超30天'
    elif days >= HOLD_REVIEW:
        status = '⚠️ 需審視'
    elif days >= HOLD_WARN:
        status = '👀 注意'
    else:
        status = '✅ 正常'

    if twii and twii['rsi'] > RSI_REDUCE_50:
        status += ' | ⚠️ TWII過熱'
    elif twii and twii['rsi'] > RSI_NEW_BAN:
        status += ' | 🟡 TWII警告'

    pos_report.append({
        'symbol': sym,
        'days': days,
        'status': status,
        'rsi': rsi,
        'pnl_pct': round(pnl_pct, 2),
        'dist_to_stop': round(dist_stop, 1),
        'dist_to_target': round(dist_target, 1),
    })
    print(f'  {sym}: {days}天 | RSI={rsi} | {pnl_pct:+.2f}% | {status}')

report['sections']['positions'] = {'positions': pos_report, 'count': len(pos_report)}

# 4. Strategy Consistency
print('\n[4/5] 策略一致性...')
prev_output = os.path.join(SHORT_TERM, 'tina_cron_v2_output.json')
prev_sentiment = None
if os.path.exists(prev_output):
    with open(prev_output, 'r', encoding='utf-8') as f:
        prev = json.load(f)
    prev_sentiment = prev.get('layer4_market', {}).get('market_sentiment')
    prev_action = prev.get('layer5_action', {}).get('label')
    print(f'  昨日行動: {prev_action} | 昨日情緒: {prev_sentiment}/100')
else:
    print('  無昨日資料（首次執行）')
    prev_action = None

current_action = 'WATCH' if (twii and twii['rsi'] > RSI_NEW_BAN) else 'BUY'
consistency = 'CONSISTENT' if prev_action == current_action else f'CHANGED: {prev_action} → {current_action}'
print(f'  今日行動: {current_action} | {consistency}')
report['sections']['strategy'] = {
    'prev_action': prev_action,
    'current_action': current_action,
    'consistency': consistency,
}

# 5. Memory System Health
print('\n[5/5] 記憶系統健康...')
mem_stats = get_memory_stats()
print(f'  Short-term 檔案: {mem_stats["short_term_files"]}')
for lt in mem_stats['long_term']:
    print(f'  {lt["file"]}: {lt["count"]} 筆')
print(f'  上次蒸餾: {mem_stats["last_distillation"]}')
report['sections']['memory'] = mem_stats

# ═══ 最終評分 ═══
print('\n===========================================')
print(' 健康報告摘要')
print('===========================================')

# 評分（0-100）
health_score = 80
issues = []

if db_health['status'] != 'OK': health_score -= 10; issues.append('DB異常')
if cron_health.get('status') != 'OK': health_score -= 10; issues.append('Cron異常')
if twii and twii['rsi'] > RSI_REDUCE_50: health_score -= 20; issues.append(f'TWII過熱 RSI={twii["rsi"]}')
if vix and vix > 25: health_score -= 10; issues.append(f'VIX高={vix}')
if len(positions) > 0:
    overdue = [p for p in pos_report if p['days'] >= HOLD_WARN]
    if overdue: health_score -= 5; issues.append(f'{len(overdue)}口持有超20天')

health_label = '🟢 健康' if health_score >= 80 else '🟡 注意' if health_score >= 60 else '🟠 警告' if health_score >= 40 else '🔴 危險'
print(f'  系統評分: {health_score}/100 {health_label}')
for issue in issues:
    print(f'  ⚠️ {issue}')

report['summary'] = {
    'health_score': health_score,
    'health_label': health_label,
    'issues': issues,
}

# 寫入輸出
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'\n已寫入: {OUTPUT}')
print(f'完成: {datetime.now().strftime("%H:%M:%S")}')