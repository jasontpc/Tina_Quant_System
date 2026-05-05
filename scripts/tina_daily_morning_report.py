import yfinance as yf
import numpy as np
import pandas as pd
import json
from datetime import datetime

# ========================
# Tina Brain Daily Morning Report v2
# 2026-05-04
# ========================

with open('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/hunter_watch_list.json', encoding='utf-8') as f:
    wl = json.load(f)
with open('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/teams/nana/monitor_stocks.json', encoding='utf-8') as f:
    nana = json.load(f)
with open('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/teams/leo/leo_watchlist.json', encoding='utf-8') as f:
    leo = json.load(f)

# ========================
# Market Overview
# ========================
print('=' * 55)
print('  Tina 大腦每日晨報 — ' + datetime.now().strftime('%Y-%m-%d 08:00'))
print('=' * 55)
print()

print('【市場概況】')
print('-' * 55)

try:
    twii = yf.Ticker('^TWII').history(period='5d')
    if len(twii) >= 2:
        tc = float(twii['Close'].iloc[-1])
        tp = float(twii['Close'].iloc[-2])
        tchg = (tc-tp)/tp*100
        print(f'  TWII   {tc:>10,.0f}  {tchg:+.2f}%')
except: print('  TWII   N/A')

try:
    spx = yf.Ticker('^SPX').history(period='5d')
    if len(spx) >= 2:
        sc = float(spx['Close'].iloc[-1])
        sp = float(spx['Close'].iloc[-2])
        schg = (sc-sp)/sp*100
        print(f'  SPX    {sc:>10,.0f}  {schg:+.2f}%')
except: print('  SPX    N/A')

try:
    nasdaq = yf.Ticker('^IXIC').history(period='5d')
    if len(nasdaq) >= 2:
        nc = float(nasdaq['Close'].iloc[-1])
        np_ = float(nasdaq['Close'].iloc[-2])
        nchg = (nc-np_)/np_*100
        print(f'  NASDAQ {nc:>10,.0f}  {nchg:+.2f}%')
except: print('  NASDAQ N/A')

try:
    vix = yf.Ticker('^VIX').history(period='5d')
    if len(vix) >= 1:
        vc = float(vix['Close'].iloc[-1])
        vix_status = '偏高二好在 18+)' if vc > 18 else '市場情緒穩定' if vc > 14 else '極度低估'
        print(f'  VIX    {vc:>10.2f}  ({vix_status})')
except: print('  VIX    N/A')

# Gold/Oil
try:
    gold = yf.Ticker('GC=F').history(period='5d')
    if len(gold) >= 2:
        gc = float(gold['Close'].iloc[-1])
        gp = float(gold['Close'].iloc[-2])
        gchg = (gc-gp)/gp*100
        print(f'  GOLD  {gc:>10,.0f}  {gchg:+.2f}%')
except: pass

print()
print('【Leo 精華名單 (MA_OK — 勝率>60%)】')
print('-' * 55)
leo_stocks = sorted(leo.get('stocks', {}).items(), key=lambda x: x[1].get('win_rate', 0), reverse=True)
for sym, s in leo_stocks[:8]:
    name = s.get('name', sym)
    wr = s.get('win_rate', 0)
    pnl = s.get('avg_pnl', 0)
    pf = s.get('pf', 0)
    note = s.get('note', '')[:35]
    print(f'  {name:<8} 勝率:{wr:>5.1f}%  均報酬:{pnl:>+5.2f}%  PF:{pf:.2f}  {note}')

print()
print('【Nana 觀察名單 (MA_ADJUST — 勝率50-65%)】')
print('-' * 55)
nana_stocks = sorted(nana.get('stocks', []), key=lambda x: x.get('win_rate', 0), reverse=True)
for s in nana_stocks:
    name = s.get('name', s['stock_id'])
    wr = s.get('win_rate', 0)
    pnl = s.get('avg_pnl', 0)
    strat = s.get('strategy', '')[:40]
    print(f'  {name:<8} 勝率:{wr:>5.1f}%  均報酬:{pnl:>+5.2f}%  {strat}')

print()
print('【Hunter 替代策略追蹤 (MA_BAN)】')
print('-' * 55)
hunter = [item for item in wl.get('watch_list', []) if item.get('verdict') == 'MA_BAN']
for item in hunter[:6]:
    name = item.get('name', item['symbol'])
    strat = item.get('strategy', '')[:50]
    print(f'  {name:<12} {strat}')

print()
print('【失敗教訓提醒】')
print('-' * 55)
print('  1. 進場RSI需 <55（避免55-60區間，被掃停損）')
print('  2. 偏離MA20 >4% 不放進場（追高容易被套）')
print('  3. 電力基建/ASIC/金融股不適用MA策略')
print('  4. 停損果斷：5天持有，RSI>65即將反轉果斷離場')

print()
print('【Ray ETF DCA 觀察】')
print('-' * 55)
try:
    etfs = [('0050.TW','0050'),('00646.TW','00646'),('00878.TW','00878'),('00713.TW','00713')]
    for sym, code in etfs:
        t = yf.Ticker(sym)
        h = t.history(period='5d')
        if len(h) >= 2:
            c = float(h['Close'].iloc[-1])
            p = float(h['Close'].iloc[-2])
            chg = (c-p)/p*100
            print(f'  {code:<6} {c:>8.2f}  {chg:+.2f}%')
except: pass

print()
print('=' * 55)
print('  Tina 大腦 08:00 晨報完成')
print('=' * 55)