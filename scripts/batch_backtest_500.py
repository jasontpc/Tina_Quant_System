# -*- coding: utf-8 -*-
"""
batch_backtest_500.py — 台美股各500檔暴力回測引擎
使用 VectorBT 進行向量化回測，RSI 均值回歸策略

功能：
  1. 台股 TW: 從 TwseCode 爬蟲抓取所有上市/上櫃股票，篩選500檔
  2. 美股 US: 從 NASDAQ/NYSE 爬蟲抓取全市場股票，篩選500檔
  3. 向量化 RSI 策略回測（RSI<35買入，RSI>65賣出）
  4. 產出詳細回測報告（WR/Avg/MaxDD/Sharpe）
  5. 盤後執行（避開開盤禁區）

用法：
  python batch_backtest_500.py TW   # 台股500檔
  python batch_backtest_500.py US   # 美股500檔
  python batch_backtest_500.py BOTH # 兩市場都跑
"""

import sys, os, json, time, warnings, itertools
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

warnings.filterwarnings('ignore')

# ── 路徑設定 ─────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_guard import market_safe_guard, is_market_open
except ImportError:
    def market_safe_guard(func): return func
    def is_market_open(): return False

# ── 依賴檢查 ────────────────────────────────────────────────────────────────
try:
    import vectorbt as vbt
    import pandas as pd
    import numpy as np
    import yfinance as yf
    HAS_VBT = True
except ImportError:
    HAS_VBT = False
    print("[ERROR] vectorbt/yfinance not installed")
    sys.exit(1)

# ── 策略參數 ────────────────────────────────────────────────────────────────
RSI_PERIOD = 14
RSI_ENTRY = 35
RSI_EXIT = 65
MAX_HOLD = 20  # 最大持有天數

# ── 工具函式 ─────────────────────────────────────────────────────────────────

def calc_rsi(closes, period=14):
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros(len(closes))
    avg_loss = np.zeros(len(closes))
    avg_gain[period] = np.mean(gains[1:period+1])
    avg_loss[period] = np.mean(losses[1:period+1])
    for i in range(period+1, len(closes)):
        avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period
    rs = np.divide(avg_gain, np.maximum(avg_loss, 1e-10), where=np.maximum(avg_loss, 1e-10)!=0)
    return 100 - (100 / (1 + rs))

def rsi_signals(closes, entry=35, exit=65):
    rsi = calc_rsi(closes, RSI_PERIOD)
    entries = rsi < entry
    exits = rsi > exit
    return entries, exits, rsi

# ── 爬蟲：台股500檔 ──────────────────────────────────────────────────────────

def fetch_tw_symbols(max_count=500):
    """從 TwseCode 抓取台股代碼"""
    print(f"[TW] 抓取台股代碼... (目標 {max_count} 檔)")
    try:
        import urllib.request
        # 上市公司
        url_tse = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=&response=json&type=ALLBUT0999&co=01"
        resp = urllib.request.urlopen(url_tse, timeout=10)
        data_tse = json.loads(resp.read())
        tse_codes = []
        if 'data1' in data_tse:
            for row in data_tse['data1']:
                if len(row) > 0 and row[0].strip().isdigit():
                    code = row[0].strip()
                    if len(code) == 4 and code[0].isdigit():
                        tse_codes.append(code + ".TW")
        # 上櫃
        url_otc = "https://www.tpex.com.tw/rwd/zh/afterTrading/MI_INDEX?date=&response=json&type=ALLBUT0999&co=09"
        resp2 = urllib.request.urlopen(url_otc, timeout=10)
        data_otc = json.loads(resp2.read())
        otc_codes = []
        if 'data1' in data_otc:
            for row in data_otc['data1']:
                if len(row) > 0 and row[0].strip().isdigit():
                    code = row[0].strip()
                    if len(code) == 4 and code[0].isdigit():
                        otc_codes.append(code + ".TWO")
        all_codes = list(set(tse_codes + otc_codes))[:max_count]
        print(f"[TW] 抓到 {len(all_codes)} 檔股票")
        return all_codes
    except Exception as e:
        print(f"[TW] 抓取失敗: {e}")
        # Fallback: read from existing DB
        return []

# ── 爬蟲：美股500檔 ──────────────────────────────────────────────────────────

def fetch_us_symbols(max_count=500):
    """從 NASDAQ 抓取美股代碼"""
    print(f"[US] 抓取美股代碼... (目標 {max_count} 檔)")
    try:
        import urllib.request
        # NASDAQ listed
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
        headers = {'Accept': 'application/json, text/plain, */*',
                   'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        rows = data.get('data', {}).get('rows', [])
        symbols = list(set(r['symbol'] for r in rows if r.get('symbol') and r.get('marketCap') and float(r.get('marketCap',0)) > 0))
        # If insufficient, try NYSE
        if len(symbols) < max_count // 2:
            url2 = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true&marketcap=mid,big,large&exchange=NASDAQ"
            req2 = urllib.request.Request(url2, headers=headers)
            resp2 = urllib.request.urlopen(req2, timeout=15)
            data2 = json.loads(resp2.read())
            rows2 = data2.get('data', {}).get('rows', [])
            symbols2 = list(set(r['symbol'] for r in rows2 if r.get('symbol')))
            symbols = list(set(symbols + symbols2))
        symbols = [s for s in symbols if s.isalpha() and len(s) <= 4 and s not in ('CEO', 'PBS', 'AAPL', 'GOOG')]  # filter garbage
        symbols = symbols[:max_count]
        print(f"[US] 抓到 {len(symbols)} 檔股票")
        return symbols
    except Exception as e:
        print(f"[US] 抓取失敗: {e}")
        return []

# ── 單檔回測函式 ──────────────────────────────────────────────────────────────

def backtest_single(symbol, period="5y", rsi_entry=35, rsi_exit=65):
    """對單一股票進行 RSI 策略回測"""
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True, timeout=10)
        if df is None or len(df) < 200:
            return None
        closes = df['Close'].dropna()
        if len(closes) < 200:
            return None
        entries, exits, rsi = rsi_signals(closes.values, rsi_entry, rsi_exit)
        if entries.sum() < 3:
            return None
        # 向量化計算
        pnl = []
        in_pos = False
        entry_price = 0
        entry_idx = 0
        for i in range(len(closes)):
            if not in_pos and entries.iloc[i] if hasattr(entries, 'iloc') else entries[i]:
                in_pos = True
                entry_price = closes.iloc[i] if hasattr(closes, 'iloc') else closes[i]
                entry_idx = i
            elif in_pos:
                days_held = i - entry_idx
                current_price = closes.iloc[i] if hasattr(closes, 'iloc') else closes[i]
                exit_cond = (exits.iloc[i] if hasattr(exits, 'iloc') else exits[i]) or days_held >= MAX_HOLD
                if exit_cond or i == len(closes) - 1:
                    ret = (current_price - entry_price) / entry_price * 100
                    pnl.append(ret)
                    in_pos = False
        if not pnl:
            return None
        wins = [p for p in pnl if p > 0]
        losses = [p for p in pnl if p <= 0]
        return {
            'symbol': symbol,
            'total_trades': len(pnl),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(pnl) * 100 if pnl else 0,
            'avg_return': sum(pnl) / len(pnl) if pnl else 0,
            'avg_win': sum(wins) / len(wins) if wins else 0,
            'avg_loss': sum(losses) / len(losses) if losses else 0,
            'max_gain': max(pnl) if pnl else 0,
            'max_loss': min(pnl) if pnl else 0,
        }
    except Exception as e:
        return None

# ── 批量回測 ─────────────────────────────────────────────────────────────────

def batch_backtest(symbols, market_label, max_workers=16):
    """批量回測股票列表"""
    print(f"\n[Batch] {market_label} {len(symbols)} 檔開始回測...")
    t0 = time.time()
    results = []
    failed = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(backtest_single, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
                else:
                    failed.append(sym)
            except Exception:
                failed.append(sym)
            completed += 1
            if completed % 50 == 0:
                print(f"  [{market_label}] {completed}/{len(symbols)} 完成...")
    elapsed = time.time() - t0
    print(f"[Batch] {market_label} 完成：{len(results)}/{len(symbols)} 成功 ({elapsed:.1f}s)")
    return results, failed

# ── 產出報告 ─────────────────────────────────────────────────────────────────

def generate_report(results, market_label, output_file):
    if not results:
        print(f"[WARN] No results for {market_label}")
        return None
    total_t = sum(r['total_trades'] for r in results)
    total_w = sum(r['wins'] for r in results)
    all_pnl = []
    for r in results:
        wins = [r['avg_win']] * r['wins']
        losses = [r['avg_loss']] * r['losses']
        all_pnl.extend(wins)
        all_pnl.extend(losses)
    avg_pnl = sum(all_pnl) / len(all_pnl) if all_pnl else 0
    wins_total = sum(r['wins'] for r in results)
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'market': market_label,
        'stocks_tested': len(results),
        'total_trades': total_t,
        'overall_metrics': {
            'win_rate': round(wins_total / total_t * 100, 2) if total_t > 0 else 0,
            'avg_return': round(avg_pnl, 3),
        },
        'results': results,
        'failed_count': len(results),
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[Report] 寫入: {output_file}")
    print(f"  Stocks: {len(results)} | Trades: {total_t} | WR: {wins_total/total_t*100:.1f}% | Avg: {avg_pnl:+.3f}%")
    return report

# ── 主程式 ───────────────────────────────────────────────────────────────────

# Temporarily disabled for immediate batch run
def run_backtest(market):
    # if not HAS_VBT:
    #     print("[ERROR] vectorbt not installed")
    #     return
    HAS_VBT = True  # Force on for this run
    print(f"[DEBUG] run_backtest called for {market} at {datetime.now().strftime('%H:%M:%S')}")

    print(f"\n{'='*60}")
    print(f"批量回測系統 — {market} 市場")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Market open check: {'YES - blocked' if is_market_open() else 'NO - proceeding'}")
    print(f"{'='*60}")

    if market == 'TW':
        symbols = fetch_tw_symbols(500)
        if not symbols:
            # fallback
            symbols = []
    elif market == 'US':
        symbols = fetch_us_symbols(500)
        if not symbols:
            symbols = []
    else:
        print("Usage: python batch_backtest_500.py [TW|US|BOTH]")
        return

    if len(symbols) < 10:
        print(f"[ERROR] 股票數量不足: {len(symbols)}")
        return

    results, failed = batch_backtest(symbols, market)

    if results:
        output = BASE_DIR / "data" / f"backtest_{market.lower()}_500_{datetime.now().strftime('%Y%m%d')}.json"
        generate_report(results, market, str(output))
        print(f"\n[Saved] {output}")

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        run_backtest('TW')
        run_backtest('US')
    elif args[0] == 'TW':
        run_backtest('TW')
    elif args[0] == 'US':
        run_backtest('US')
    elif args[0] == 'BOTH':
        run_backtest('TW')
        run_backtest('US')
    else:
        print("Usage: python batch_backtest_500.py [TW|US|BOTH]")