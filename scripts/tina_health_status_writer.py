# -*- coding: utf-8 -*-
"""
Tina 大腦健康快照寫入 JSON — 供 Streamlit Cloud Brain Tab 讀取
每 30 分鐘執行（透過 cron），寫入 teams/reports/tina_health_status.json
"""
import sys, sqlite3, os, json, subprocess, urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data")
REPORT_JSON = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\reports\tina_health_status.json")
OPENCLAW_CLI = r"C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"

def get_db_info(db_name):
    db_path = DATA_DIR / db_name
    if not db_path.exists():
        return {'latest': None, 'age_days': 999, 'size_mb': 0, 'tables': 0, 'status': 'missing'}
    size = db_path.stat().st_size
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    latest = None
    for t in tables[:8]:
        for col in ['date', 'Date', 'updated_at']:
            try:
                d = cur.execute(f'SELECT MAX({col}) FROM "{t}"').fetchone()[0]
                if d and (not latest or str(d) > str(latest)):
                    latest = str(d)[:10]
            except: pass
    conn.close()
    size_mb = size / 1024 / 1024
    age = 999
    if latest:
        try:
            age = (datetime.now().date() - datetime.strptime(latest, '%Y-%m-%d').date()).days
        except: age = 999
    return {'latest': latest, 'age_days': age, 'size_mb': round(size_mb, 2), 'tables': len(tables), 'status': 'ok' if age < 999 else 'stale'}

def check_gateway():
    try:
        req = urllib.request.Request('http://127.0.0.1:18789/health', timeout=3)
        with urllib.request.urlopen(req, timeout=3) as resp:
            gw_data = json.loads(resp.read())
        return {'status': 'online', 'uptime': gw_data.get('uptime', 'N/A')}
    except:
        return {'status': 'offline', 'uptime': 'N/A'}

def check_cron():
    try:
        out = subprocess.run(['node', OPENCLAW_CLI, 'cron', 'list'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=25).stdout
        lines = out.splitlines()
        crons = {}
        for line in lines:
            if len(line) > 35 and line[0] not in (' ', '\t', ' '):
                parts = line.split()
                if len(parts) >= 2:
                    cid = parts[0]
                    name = ' '.join(parts[1:])
                    crons[cid] = {'name': name, 'status': 'unknown'}
        for line in lines:
            for cid in crons:
                if cid in line:
                    if 'error' in line.lower(): crons[cid]['status'] = 'error'
                    elif 'ok' in line.lower(): crons[cid]['status'] = 'ok'
                    elif 'idle' in line.lower(): crons[cid]['status'] = 'idle'
                    elif 'running' in line.lower(): crons[cid]['status'] = 'running'
                    break
        ok_c = sum(1 for v in crons.values() if v['status'] == 'ok')
        err_c = sum(1 for v in crons.values() if v['status'] == 'error')
        idl_c = sum(1 for v in crons.values() if v['status'] == 'idle')
        run_c = sum(1 for v in crons.values() if v['status'] == 'running')
        err_jobs = [v['name'] for v in crons.values() if v['status'] == 'error']
        return {'total': len(crons), 'ok': ok_c, 'error': err_c, 'idle': idl_c, 'running': run_c, 'error_jobs': err_jobs}
    except Exception as e:
        return {'total': 0, 'ok': 0, 'error': 0, 'idle': 0, 'running': 0, 'error_jobs': [], 'err': str(e)}

def get_market():
    try:
        import yfinance as yf
        twii = yf.Ticker('^TWII').history(period='5d')['Close']
        twii_chg = float((twii.iloc[-1] / twii.iloc[-2] - 1) * 100) if len(twii) >= 2 else 0
        delta = twii.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, float('nan'))
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        signal = 'overbought' if rsi > 70 else ('oversold' if rsi < 40 else 'neutral')
        return {'twii': float(twii.iloc[-1]), 'twii_chg': round(twii_chg, 2), 'twii_rsi': round(rsi, 1), 'signal': signal}
    except:
        return {'twii': None, 'twii_chg': None, 'twii_rsi': None, 'signal': 'unknown'}

# Build snapshot
snapshot = {
    'updated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
    'version': 1,
    'gateway': check_gateway(),
    'dbs': {name: get_db_info(f'{name}.db') for name in [
        'yfinance', 'macro_institutional', 'etf', 'tw_history', 'leo_stocks', 'finmind'
    ]},
    'cron_summary': check_cron(),
    'market': get_market(),
    'portfolio': {
        '00713': {'name': '元大高息低波', 'qty': 300, 'cost': 53.22}
    }
}

# Add portfolio live price
try:
    import yfinance as yf
    price = float(yf.Ticker('00713.TW').history(period='1d')['Close'].iloc[-1])
    snapshot['portfolio']['00713']['price'] = price
    cost = snapshot['portfolio']['00713']['cost']
    qty = snapshot['portfolio']['00713']['qty']
    pnl = round((price - cost) * qty, 0)
    pnl_pct = round((price / cost - 1) * 100, 2)
    snapshot['portfolio']['00713']['pnl'] = pnl
    snapshot['portfolio']['00713']['pnl_pct'] = pnl_pct
except: pass

# Write JSON
REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(REPORT_JSON, 'w', encoding='utf-8') as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)

print(f"Health snapshot written: {REPORT_JSON}")
print(f"Gateway: {snapshot['gateway']['status']}")
print(f"DBs: {', '.join(k for k,v in snapshot['dbs'].items() if v['status']=='ok')}")
print(f"Cron: {snapshot['cron_summary']['total']} total, {snapshot['cron_summary']['error']} errors")
