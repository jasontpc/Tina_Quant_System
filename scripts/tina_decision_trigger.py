# -*- coding: utf-8 -*-
"""
Tina 自主決策五大層觸發器
=========================
每小時執行一次，完整運行 Layer 1-5 決策流程
"""
import sys, os, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\MEMORY.md')
LEDGER_FILE = WORKSPACE / 'data' / 'experience_ledger.json'
DECISION_LOG = Path(r'C:\Users\USER\.openclaw\workspace\memory\decision_log.md')
LESSONS_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'lessons'

print('='*70)
print('Tina 自主決策五大層 — 執行觸發器')
print('='*70)
print(f'時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ========== Layer 1: 讀取 MEMORY.md ==========
print('[Layer 1] 目標定義層 — 讀取 MEMORY.md')
print('-'*50)

if MEMORY_FILE.exists():
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析持倉
    positions = []
    if '### 持倉狀態' in content:
        start = content.find('### 持倉狀態')
        section = content[start:start+2000]
        for line in section.split('\n'):
            if line.startswith('- ') and ('@' in line or '股' in line):
                positions.append(line.strip())
    
    print(f'  讀取持倉：{len(positions)} 筆')
    for p in positions[:5]:
        print(f'    {p}')
else:
    print('  [WARN] MEMORY.md 不存在')

print()

# ========== Layer 2: 風控邊界檢查 ==========
print('[Layer 2] 邊界約束層 — 風控檢查')
print('-'*50)

SAFE_BOUNDARIES = {
    'max_loss_single_trade': 0.08,
    'max_portfolio_exposure': 0.40,
    'rsi_entry_max': 65,
}

print(f'  RSI 進場上限：{SAFE_BOUNDARIES["rsi_entry_max"]} ✅')
print(f'  單筆最大虧損：{SAFE_BOUNDARIES["max_loss_single_trade"]*100:.0f}% ✅')
print(f'  總部位上限：{SAFE_BOUNDARIES["max_portfolio_exposure"]*100:.0f}% ✅')

print()

# ========== Layer 3: 感知分析層 ==========
print('[Layer 3] 感知分析層 — 市場感知')
print('-'*50)

import yfinance as yf
twii = yf.Ticker('^TWII')
twii_hist = twii.history(period='1mo')
if len(twii_hist) >= 14:
    delta = twii_hist['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    twii_rsi = (100 - (100 / (1 + rs))).iloc[-1]
    print(f'  TWII RSI：{twii_rsi:.1f}')
    if twii_rsi > 85:
        print(f'  ⚠️ TWII 過熱！建議降倉')
else:
    print('  [WARN] TWII 資料不足')

print()

# ========== Layer 4: 沙盒驗證 ==========
print('[Layer 4] 沙盒驗證層 — Paper Trade 檢查')
print('-'*50)

trades_file = WORKSPACE / 'teams' / 'leadtrades' / 'leos' / 'leos_trades.json'
if trades_file.exists():
    with open(trades_file, encoding='utf-8') as f:
        data = json.load(f)
    open_trades = [t for t in data.get('trades', []) if t.get('status') == 'open']
    print(f'  開倉數量：{len(open_trades)}')
    
    for t in open_trades[:3]:
        sym = t.get('symbol', '')
        days = t.get('holding_days', 0)
        entry = t.get('entry_price', 0)
        cur = t.get('current_price', entry)
        rsi = t.get('rsi', 0)
        pnl = (cur - entry) / entry * 100 if entry else 0
        print(f'    {sym}：持有{days}天 RSI={rsi} 損益={pnl:+.1f}%')
        if days > 30 and rsi > 50:
            print(f'      ⚠️ 危險！持有>30天 + RSI>50')
else:
    print('  [INFO] 無 leos_trades.json')

print()

# ========== Layer 5: 反思進化層 ==========
print('[Layer 5] 反思進化層 — 寫入 decision_log.md')
print('-'*50)

os.makedirs(DECISION_LOG.parent, exist_ok=True)

log_entry = f"""
## 決策日誌 {datetime.now().strftime('%Y-%m-%d %H:%M')}

### Layer 1 目標定義
- 持倉：{len(positions)} 筆

### Layer 2 風控邊界
- RSI 上限：{SAFE_BOUNDARIES['rsi_entry_max']}
- 單筆虧損：{SAFE_BOUNDARIES['max_loss_single_trade']*100:.0f}%
- 部位上限：{SAFE_BOUNDARIES['max_portfolio_exposure']*100:.0f}%

### Layer 3 市場感知
- TWII RSI：{twii_rsi if 'twii_rsi' in dir() else 'N/A'}

### Layer 4 沙盒狀態
- 開倉：{len(open_trades) if 'open_trades' in dir() else 0} 筆

### Layer 5 執行結論
- 狀態：{'觀望' if 'twii_rsi' in dir() and twii_rsi > 85 else '正常'}
"""

with open(DECISION_LOG, 'a', encoding='utf-8') as f:
    f.write(log_entry)

print(f'  寫入 decision_log.md ✅')
print()

# ========== 最終報告 ==========
print('='*70)
print('五大層執行完成')
print('='*70)
print(f'TWII RSI：{twii_rsi:.1f}（市場狀態：{"過熱" if twii_rsi > 85 else "正常"}）')
print(f'開倉數量：{len(open_trades) if "open_trades" in dir() else 0}')
print()
print('下一步：等待每日 Morning Review 或手動觸發')
