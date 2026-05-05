# -*- coding: utf-8 -*-
"""
Data Audit Script — Tina Quant System
驗證所有資料庫數據一致性
"""
import sys
import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 路徑設定
# ============================================================
WORKSPACE = r'C:\Users\USER\.openclaw\workspace'
MEMORY_FILE = os.path.join(WORKSPACE, 'MEMORY.md')
INSTITUTIONAL_FILE = os.path.join(WORKSPACE, 'memory', 'institutional_stocks.json')
FIXES_FILE = os.path.join(WORKSPACE, 'memory', 'data_audit_fixes.md')
NANA_SECTORS_DIR = os.path.join(WORKSPACE, 'Tina_Quant_System', 'teams', 'nana', 'sectors')
NANA_TIERS_DIR = os.path.join(WORKSPACE, 'Tina_Quant_System', 'teams', 'nana', 'tiers')
RAY_ALERT_FILE = os.path.join(WORKSPACE, 'Tina_Quant_System', 'teams', 'ray', 'ray_alert_agent.py')

FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

os.makedirs(os.path.join(WORKSPACE, 'memory'), exist_ok=True)

# ============================================================
# 工具函數
# ============================================================
def get_current_price(stock_id: str) -> Optional[float]:
    """用 yfinance 抓取現價"""
    sym = stock_id + '.TW'
    try:
        t = yf.Ticker(sym)
        h = t.history(period='5d')
        if h.empty:
            return None
        close = h['Close']
        if hasattr(close, 'squeeze'):
            close = close.squeeze()
        return float(close.iloc[-1])
    except Exception:
        return None

def get_etf_price(etf_id: str) -> Optional[float]:
    """用 yfinance 抓取 ETF 現價"""
    sym = etf_id + '.TW'
    try:
        t = yf.Ticker(sym)
        h = t.history(period='5d')
        if h.empty:
            return None
        close = h['Close']
        if hasattr(close, 'squeeze'):
            close = close.squeeze()
        return float(close.iloc[-1])
    except Exception:
        return None

def calc_wr(stock_id: str) -> Optional[float]:
    """計算 N 日價格Position"""
    sym = stock_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1mo')
        if h.empty or len(h) < 20:
            return None
        close = h['Close']
        if hasattr(close, 'squeeze'):
            close = close.squeeze()
        low = close.min()
        high = close.max()
        price = close.iloc[-1]
        if high == low:
            return 50.0
        wr = (price - low) / (high - low) * 100
        return round(wr, 1)
    except Exception:
        return None

def check_taiwan_stock(stock_id: str) -> bool:
    """驗證股票是否真實存在"""
    sym = stock_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1d')
        return not h.empty
    except Exception:
        return False

def check_etf(etf_id: str) -> bool:
    """驗證 ETF 是否真實存在"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1d')
        return not h.empty
    except Exception:
        return False

# ============================================================
# 修復記錄
# ============================================================
fixes = []
now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

def log_fix(category: str, stock_id: str, issue: str, old_val, new_val):
    fixes.append({
        'time': now_str,
        'category': category,
        'stock_id': stock_id,
        'issue': issue,
        'old': old_val,
        'new': new_val
    })

# ============================================================
# 1. Nana Sector Stocks 驗證
# ============================================================
print('=' * 60)
print('1. Nana Sector Stocks 驗證')
print('=' * 60)

sector_dirs = ['ai_hvdc', 'defense', 'finance', 'general']
sector_fixes = []

for sec in sector_dirs:
    fpath = os.path.join(NANA_SECTORS_DIR, sec, 'stocks.json')
    if not os.path.exists(fpath):
        print(f'[SKIP] {sec}/stocks.json 不存在')
        continue

    with open(fpath, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    print(f'\n--- {sec} ({len(stocks)} 檔) ---')

    for stock in stocks:
        sid = stock['id']
        name = stock.get('name', '?')
        existing_price = stock.get('price')
        verified = stock.get('verified')

        # 檢查股票是否存在
        exists = check_taiwan_stock(sid)
        if not exists:
            print(f'  ❌ {sid} {name} — 股票不存在！')
            sector_fixes.append({'sid': sid, 'name': name, 'sec': sec, 'action': 'REMOVE_MISSING'})
            continue

        # 抓現價
        price = get_current_price(sid)
        if price is None:
            print(f'  ⚠️  {sid} {name} — 無法抓取價格')
            continue

        # 檢查價格偏離
        if existing_price:
            diff_pct = abs(price - existing_price) / existing_price * 100
            if diff_pct > 50:
                print(f'  ⚠️  {sid} {name} — 價格偏離 {diff_pct:.1f}% (記錄${existing_price} vs 實際${price:.2f})')
                sector_fixes.append({
                    'sid': sid, 'name': name, 'sec': sec,
                    'action': 'UPDATE_PRICE',
                    'old_price': existing_price,
                    'new_price': round(price, 2),
                    'diff_pct': round(diff_pct, 1)
                })
            elif diff_pct > 20:
                print(f'  ~  {sid} {name} — 價格差 {diff_pct:.1f}% (記錄${existing_price} vs 實際${price:.2f})')
            else:
                print(f'  ✅ {sid} {name} — ${price:.2f} (WR check...)')

            # 更新 WR
            wr = calc_wr(sid)
            old_wr = stock.get('wr')
            if wr and (old_wr is None or abs(wr - old_wr) > 15):
                sector_fixes.append({
                    'sid': sid, 'name': name, 'sec': sec,
                    'action': 'UPDATE_WR',
                    'old_wr': old_wr,
                    'new_wr': wr
                })
        else:
            print(f'  ✅ {sid} {name} — ${price:.2f} (new/no-price)')

# ============================================================
# 2. Nana Tier Stocks 驗證
# ============================================================
print('\n' + '=' * 60)
print('2. Nana Tier Stocks 驗證')
print('=' * 60)

tier_dirs = ['tier1', 'tier2', 'tier3']
tier_fixes = []

for td in tier_dirs:
    fpath = os.path.join(NANA_TIERS_DIR, td, 'stocks.json')
    if not os.path.exists(fpath):
        print(f'[SKIP] {td}/stocks.json 不存在')
        continue

    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stocks = data.get('stocks', [])
    print(f'\n--- {td} ({len(stocks)} 檔) ---')

    for stock in stocks:
        sid = stock['id']
        name = stock.get('name', '?')
        tier = stock.get('tier', '?')

        exists = check_taiwan_stock(sid)
        if not exists:
            print(f'  ❌ {sid} {name} — 股票不存在！')
            tier_fixes.append({'sid': sid, 'name': name, 'tier': td, 'action': 'REMOVE_MISSING'})
            continue

        price = get_current_price(sid)
        if price is None:
            print(f'  ⚠️  {sid} {name} — 無法抓取價格')
            continue

        print(f'  ✅ {sid} {name} — ${price:.2f}')

        # Tier 合理性檢查（WR 65+ 應在 tier1/2，55-65 tier2/3）
        wr = calc_wr(sid)
        old_wr = stock.get('wr')
        if wr:
            if wr >= 65 and tier not in ['1', '2']:
                print(f'  ⚠️  {sid} WR={wr}% 却在 tier{tier}（建議 tier1/2）')
                tier_fixes.append({'sid': sid, 'name': name, 'tier': td, 'action': 'TIER_MISMATCH', 'wr': wr})
            elif wr >= 55 and tier == '3' and wr < 65:
                print(f'  ℹ️  {sid} WR={wr}% 在 tier3 合理')
        if wr and old_wr and abs(wr - old_wr) > 15:
            tier_fixes.append({'sid': sid, 'name': name, 'tier': td, 'action': 'UPDATE_WR', 'old_wr': old_wr, 'new_wr': wr})

# ============================================================
# 3. Ray ETF Monitor 驗證
# ============================================================
print('\n' + '=' * 60)
print('3. Ray ETF Monitor 驗證')
print('=' * 60)

ETF_LIST = [
    '0050', '0056', '00878', '00881', '00891',
    '00915', '00919', '00923', '00927',
    '00713', '00646', '00662', '00757',
    '00762', '00895'
]
ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00881': '國泰台灣5G', '00891': '中信低碳', '00915': '富邦台灣永續高息',
    '00919': '群益台灣精選', '00923': '群益台灣ESG低碳', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00762': '元大石油', '00895': '富邦上証'
}

etf_fixes = []
for etf in ETF_LIST:
    name = ETF_NAMES.get(etf, etf)
    price = get_etf_price(etf)
    exists = check_etf(etf)
    if not exists:
        print(f'  ❌ {etf} {name} — ETF 不存在！')
        etf_fixes.append({'etf': etf, 'name': name, 'action': 'REMOVE_MISSING'})
    elif price is None:
        print(f'  ⚠️  {etf} {name} — 無法抓取價格')
    else:
        print(f'  ✅ {etf} {name} — ${price:.2f}')

# ============================================================
# 4. MEMORY.md ETF 進場價驗證
# ============================================================
print('\n' + '=' * 60)
print('4. MEMORY.md ETF 進場價驗證')
print('=' * 60)

memory_etf_targets = {
    '0050': 77, '00646': 66, '00662': 100, '00757': 110,
    '00713': 51, '0056': 38, '00927': 25
}

memory_fixes = []
for etf, target_price in memory_etf_targets.items():
    current = get_etf_price(etf)
    name = ETF_NAMES.get(etf, etf)
    if current:
        diff_pct = abs(current - target_price) / target_price * 100
        if diff_pct > 30:
            print(f'  ⚠️  {etf} {name} — 理想價${target_price}偏離 {diff_pct:.1f}% (實際${current:.2f})')
            memory_fixes.append({
                'etf': etf, 'name': name,
                'old_target': target_price,
                'actual': round(current, 2),
                'diff_pct': round(diff_pct, 1)
            })
        else:
            print(f'  ✅ {etf} {name} — 理想${target_price} vs 實際${current:.2f} ({diff_pct:.1f}% diff)')
    else:
        print(f'  ❌ {etf} {name} — 無法抓取')

# ============================================================
# 5. Institutional DB 驗證
# ============================================================
print('\n' + '=' * 60)
print('5. Institutional DB 驗證')
print('=' * 60)

with open(INSTITUTIONAL_FILE, 'r', encoding='utf-8') as f:
    inst_db = json.load(f)

stock_ids = inst_db.get('stocks', [])
inst_data = inst_db.get('institutional_data', {})

print(f'機構覆蓋數量: {len(stock_ids)} 檔')
missing_stocks = []
no_inst_data = []
for sid in stock_ids:
    exists = check_taiwan_stock(sid)
    if not exists:
        print(f'  ❌ {sid} — 股票不存在！')
        missing_stocks.append(sid)
    elif sid not in inst_data or not inst_data.get(sid):
        no_inst_data.append(sid)

print(f'  缺失法人資料: {len(no_inst_data)} 檔')
if no_inst_data:
    print(f'  ID列表: {no_inst_data[:20]}')

# ============================================================
# 寫入修正記錄
# ============================================================
print('\n' + '=' * 60)
print('6. 寫入修正記錄')
print('=' * 60)

lines = [f'# Data Audit Fixes — {now_str}', '']

# Sector fixes
if sector_fixes:
    lines.append('## Sector Stocks 修正')
    for f in sector_fixes:
        if f['action'] == 'REMOVE_MISSING':
            lines.append(f'- ❌ [{f["sec"]}] `{f["sid"]}` {f["name"]} — 股票不存在，建議移除')
        elif f['action'] == 'UPDATE_PRICE':
            lines.append(f'- ⚠️  [{f["sec"]}] `{f["sid"]}` {f["name"]} — 價格偏離 {f["diff_pct"]}% (${f["old_price"]} → ${f["new_price"]})')
        elif f['action'] == 'UPDATE_WR':
            lines.append(f'- ~  [{f["sec"]}] `{f["sid"]}` {f["name"]} — WR 更新 ({f["old_wr"]} → {f["new_wr"]})')
    lines.append('')

# Tier fixes
if tier_fixes:
    lines.append('## Tier Stocks 修正')
    for f in tier_fixes:
        if f['action'] == 'REMOVE_MISSING':
            lines.append(f'- ❌ [{f["tier"]}] `{f["sid"]}` {f["name"]} — 股票不存在，建議移除')
        elif f['action'] == 'TIER_MISMATCH':
            lines.append(f'- ⚠️  [{f["tier"]}] `{f["sid"]}` {f["name"]} — WR={f["wr"]}% 與 tier 不匹配')
        elif f['action'] == 'UPDATE_WR':
            lines.append(f'- ~  [{f["tier"]}] `{f["sid"]}` {f["name"]} — WR 更新 ({f["old_wr"]} → {f["new_wr"]})')
    lines.append('')

# ETF fixes
if etf_fixes:
    lines.append('## Ray ETF 修正')
    for f in etf_fixes:
        if f['action'] == 'REMOVE_MISSING':
            lines.append(f'- ❌ `{f["etf"]}` {f["name"]} — ETF 不存在，建議從 ray_alert_agent.py 移除')
    lines.append('')

# MEMORY fixes
if memory_fixes:
    lines.append('## MEMORY.md ETF 進場價修正')
    for f in memory_fixes:
        lines.append(f'- ⚠️  `{f["etf"]}` {f["name"]} — 理想價${f["old_target"]} 偏離 {f["diff_pct"]}% (實際${f["actual"]})')
    lines.append('')

# Institutional DB
if missing_stocks:
    lines.append('## Institutional DB — 不存在股票')
    for sid in missing_stocks:
        lines.append(f'- ❌ `{sid}` — 股票不存在，建議從 institutional_stocks.json 移除')
    lines.append('')

if no_inst_data:
    lines.append(f'## Institutional DB — 無法人資料 ({len(no_inst_data)} 檔)')
    lines.append(f'- 需要抓取: {no_inst_data}')
    lines.append('')

lines.append('---')
lines.append(f'_稽核時間: {now_str}_')

fix_content = '\n'.join(lines)
with open(FIXES_FILE, 'w', encoding='utf-8') as f:
    f.write(fix_content)

print(f'修正記錄已寫入: {FIXES_FILE}')
print(f'\n發現問題汇总:')
print(f'  Sector 修正: {len(sector_fixes)} 項')
print(f'  Tier 修正: {len(tier_fixes)} 項')
print(f'  ETF 修正: {len(etf_fixes)} 項')
print(f'  MEMORY 修正: {len(memory_fixes)} 項')
print(f'  Institutional 不存在: {len(missing_stocks)} 檔')
print(f'  Institutional 無資料: {len(no_inst_data)} 檔')

print('\n✅ 稽核完成！')
