"""Auto-Learner: 自動學習擴充本地資料庫
====================================
目標：根據市場分析結果自動發現並新增值得追蹤的標的

觸發時機：
1. Leo/分析腳本發現新標的 → 寫入 candidate_watchlist
2. 當系統評估該標的值得納入時 → 自動新增至 yfinance.db
3. 每日收盤更新時自動擴充候選名單
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Tina 標準化框架
sys.path.insert(0, str(Path(__file__).parent.parent / 'stores'))
from script_standards import ScriptStandard

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'yfinance.db')
CANDIDATE_PATH = os.path.join(WORKSPACE, 'data', 'candidate_watchlist.json')
LOG_DIR = os.path.join(WORKSPACE, 'logs')


def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def load_candidates():
    """載入候選名單"""
    if os.path.exists(CANDIDATE_PATH):
        with open(CANDIDATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'candidates': [], 'learned': [], 'rejected': []}


def save_candidates(data):
    with open(CANDIDATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_candidate(symbol, reason, source='auto', score=50):
    """新增候選標的"""
    data = load_candidates()
    existing = {c['symbol'] for c in data['candidates']}
    if symbol in existing or symbol in data['learned']:
        return False

    data['candidates'].append({
        'symbol': symbol,
        'reason': reason,
        'source': source,
        'score': score,
        'added_at': datetime.now().isoformat(),
        'status': 'pending'
    })
    save_candidates(data)
    return True


def get_new_symbols_from_db(conn, min_score=50):
    """從本地資料庫學習，找出值得擴充的標的"""
    import yfinance as yf
    import pandas as pd

    data = load_candidates()
    pending = [c for c in data['candidates'] if c.get('status') == 'pending' and c.get('score', 0) >= min_score]

    candidates_to_add = []
    for c in pending:
        sym = c['symbol']
        # 檢查是否已在 DB
        c_db = conn.cursor()
        c_db.execute('SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=?', (sym,))
        count = c_db.fetchone()[0]
        if count == 0:
            # 檢查 yfinance 是否可用
            try:
                tk = yf.Ticker(sym)
                hist = tk.history(period='5d')
                if not hist.empty:
                    candidates_to_add.append(c)
            except Exception:
                pass

    return candidates_to_add


def fetch_new_symbol(conn, symbol):
    """抓取單一標的並寫入 DB"""
    import yfinance as yf
    import pandas as pd

    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period='max', auto_adjust=True)
        if hist.empty:
            return 0

        df = hist.copy()
        close = df['Close']
        df['sma_20'] = close.rolling(20).mean()
        df['sma_60'] = close.rolling(60).mean()
        df['sma_120'] = close.rolling(120).mean()
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float('inf'))
        df['rsi_14'] = 100 - (100 / (1 + rs))
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = high_low.combine(high_close, max).combine(low_close, max)
        df['atr_14'] = tr.rolling(14).mean()
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_sig'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_sig']
        bb_middle = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['bb_upper'] = bb_middle + (bb_std * 2)
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_middle - (bb_std * 2)
        df['vol_sma20'] = df['Volume'].rolling(20).mean()
        df['vol_ratio'] = df['Volume'] / df['vol_sma20']
        df['change_pct'] = close.pct_change() * 100
        df.index = df.index.strftime('%Y-%m-%d')

        c = conn.cursor()
        saved = 0
        for idx, row in df.iterrows():
            try:
                c.execute('''
                    INSERT OR REPLACE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume, change_pct,
                     sma_20, sma_60, sma_120, rsi_14, atr_14,
                     macd, macd_sig, macd_hist,
                     bb_upper, bb_middle, bb_lower, vol_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, idx,
                    row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume']),
                    round(float(row['change_pct']), 4) if pd.notna(row['change_pct']) else None,
                    round(float(row['sma_20']), 4) if pd.notna(row['sma_20']) else None,
                    round(float(row['sma_60']), 4) if pd.notna(row['sma_60']) else None,
                    round(float(row['sma_120']), 4) if pd.notna(row['sma_120']) else None,
                    round(float(row['rsi_14']), 4) if pd.notna(row['rsi_14']) else None,
                    round(float(row['atr_14']), 4) if pd.notna(row['atr_14']) else None,
                    round(float(row['macd']), 4) if pd.notna(row['macd']) else None,
                    round(float(row['macd_sig']), 4) if pd.notna(row['macd_sig']) else None,
                    round(float(row['macd_hist']), 4) if pd.notna(row['macd_hist']) else None,
                    round(float(row['bb_upper']), 4) if pd.notna(row['bb_upper']) else None,
                    round(float(row['bb_middle']), 4) if pd.notna(row['bb_middle']) else None,
                    round(float(row['bb_lower']), 4) if pd.notna(row['bb_lower']) else None,
                    round(float(row['vol_ratio']), 4) if pd.notna(row['vol_ratio']) else None,
                ))
                saved += 1
            except Exception:
                pass
        conn.commit()
        return saved
    except Exception as e:
        return 0


def auto_learn():
    """自動學習主流程"""
    print(f'\n[Tina Auto-Learner v2]')
    print('=' * 60)

    data = load_candidates()
    conn = get_db_conn()

    # 1. Get pending candidates
    pending = [c for c in data['candidates'] if c.get('status') == 'pending']
    print(f'\n[1] Pending candidates: {len(pending)}')
    for c in pending:
        print(f'  - {c["symbol"]}: {c["reason"]} (score={c["score"]}, source={c["source"]})')

    # 2. Fetch new symbols
    print(f'\n[2] Fetching new symbols...')
    new_additions = 0
    for c in pending:
        sym = c['symbol']
        # 檢查是否已在 DB
        c_db = conn.cursor()
        c_db.execute('SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=?', (sym,))
        if c_db.fetchone()[0] > 0:
            print(f'  [SKIP] {sym}: already in DB')
            c['status'] = 'skipped'
            continue

        print(f'  [ADD] {sym}...', end=' ', flush=True)
        saved = fetch_new_symbol(conn, sym)
        if saved > 0:
            c['status'] = 'learned'
            data['learned'].append({
                'symbol': sym,
                'added_at': datetime.now().isoformat(),
                'rows_added': saved,
                'reason': c['reason'],
                'source': c['source']
            })
            new_additions += 1
            print(f'{saved} rows')
        else:
            c['status'] = 'failed'
            print('FAILED')

    # 3. Update DB summary
    print(f'\n[3] DB Summary...')
    c_db = conn.cursor()
    c_db.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = c_db.fetchone()[0]
    c_db.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
    syms = [r[0] for r in c_db.fetchall()]
    print(f'  Total: {total:,} rows / {len(syms)} symbols')
    print(f'  Symbols: {sorted(syms)}')

    # 4. Clean old candidates
    data['candidates'] = [c for c in data['candidates'] if c.get('status') == 'pending']
    save_candidates(data)

    conn.close()
    print(f'\n[OK] New additions: {new_additions}')
    print('[DONE]')
    return {'new_additions': new_additions}


def suggest_from_analysis(symbols_found, reason='from analysis'):
    """從分析腳本建議新增標的"""
    data = load_candidates()
    added = 0
    for sym in symbols_found:
        # Check if in DB already
        conn = get_db_conn()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=?', (sym,))
        in_db = c.fetchone()[0] > 0
        conn.close()
        if in_db:
            continue

        if add_candidate(sym, reason, source='analysis', score=50):
            added += 1
    return added


if __name__ == '__main__':
    # Tina 標準化入口
    std = ScriptStandard('auto_learner', 'MULTI')
    
    try:
        context = std.before_execute()
        print(f"[Brain-Aware] Execution ID: {context['execution_id']}")
        
        result = auto_learn()
        
        # 讀取 candidate_watchlist.json 作為 signals
        candidate_path = os.path.join(WORKSPACE, 'data', 'candidate_watchlist.json')
        if os.path.exists(candidate_path):
            with open(candidate_path, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            signals = candidates.get('candidates', [])[:10]  # 最多 10 個
            metrics = {
                'candidates_pending': len(candidates.get('candidates', [])),
                'learned': len(candidates.get('learned', [])),
                'rejected': len(candidates.get('rejected', []))
            }
        else:
            signals = []
            metrics = {}
        
        metrics['new_additions'] = result.get('new_additions', 0)
        std.after_execute(success=True, signals=signals, metrics=metrics)
        
    except Exception as e:
        std.handle_error(e, 'tina_auto_learner.py 執行失敗')
        std.after_execute(success=False, signals=[], metrics={'error': str(e)})
        raise
    finally:
        health = std.finalize()
        print(f"[Health] status={health['status']}, duration={health['duration_ms']}ms")
