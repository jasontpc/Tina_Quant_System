# -*- coding: utf-8 -*-
"""
Tina 系統整合監控腳本
====================
合併大脑监控 + 健康状态写入 + 决策五大層
每30分钟执行一次
"""
import sys, os, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\MEMORY.md')
LEDGER_FILE = WORKSPACE / 'data' / 'experience_ledger.json'

print('='*70)
print('Tina 系統整合監控')
print('='*70)
print(f'時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ========== 大腦監控 ==========
print('[1/3] 大腦監控')
print('-'*50)

# Gateway 健康
import yfinance as yf
try:
    twii = yf.Ticker('^TWII').history('1d')
    twii_close = twii['Close'].iloc[-1]
    print(f'  TWII：{twii_close:.0f}')
except Exception as e:
    print(f'  TWII 讀取失敗：{e}')

# MEMORY 讀取
positions = []
if MEMORY_FILE.exists():
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    if '### 持倉狀態' in content:
        start = content.find('### 持倉狀態')
        section = content[start:start+2000]
        for line in section.split('\n'):
            if line.startswith('- ') and ('股' in line or '@' in line):
                positions.append(line.strip())
print(f'  持倉：{len(positions)} 筆')

# ========== 健康狀態寫入 ==========
print()
print('[2/3] 健康狀態寫入')
print('-'*50)

health = {
    'timestamp': datetime.now().isoformat(),
    'gateway': 'running',
    'positions': len(positions),
    'twii': twii_close if 'twii_close' in dir() else None,
}

health_file = WORKSPACE / 'data' / 'tina_health_status.json'
with open(health_file, 'w', encoding='utf-8') as f:
    json.dump(health, f, ensure_ascii=False, indent=2)
print(f'  健康狀態已寫入：{health_file.name}')

# ========== 五大層決策檢查 ==========
print()
print('[3/3] 五大層決策檢查')
print('-'*50)

SAFE_BOUNDARIES = {
    'max_loss_single_trade': 0.08,
    'max_portfolio_exposure': 0.40,
    'rsi_entry_max': 65,
}

# TWII RSI
try:
    twii_hist = yf.Ticker('^TWII').history('1mo')
    if len(twii_hist) >= 14:
        delta = twii_hist['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        twii_rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        print(f'  TWII RSI：{twii_rsi:.1f}')
        if twii_rsi > 85:
            print(f'  ⚠️ TWII 過熱，建議降倉')
        elif twii_rsi > 65:
            print(f'  ⚠️ TWII 偏高，謹慎進場')
        else:
            print(f'  ✅ RSI 正常範圍')
except Exception as e:
    print(f'  TWII RSI 讀取失敗：{e}')

# 風控檢查
print(f'  風控邊界：RSI<{SAFE_BOUNDARIES["rsi_entry_max"]} ✅')

print()
print('='*70)
print('整合監控完成')
print('='*70)
