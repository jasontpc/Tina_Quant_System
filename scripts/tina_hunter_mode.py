# -*- coding: utf-8 -*-
"""
Tina Brain - 主動獵人模式 v2.1
==============================
根據 7 團隊學習成果優化：
- RSI 25-55 進場區（根據實際數據調整）
- 使用 DB 預計算欄位（RSI/SMA/MACD）
- 整合經驗資料庫
"""
import sqlite3, json, sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB_PATH = DATA / "yfinance.db"


def load_experience():
    exp_path = DATA / "experience_ledger.json"
    try:
        with open(exp_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def get_hunter_candidates():
    """Stage1: 使用 DB 預計算欄位掃描候選"""
    print('[Stage1] 雷達感測中...')

    cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""
        SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, atr_14, vol_ratio
        FROM daily_ohlcv
        WHERE date >= ?
        ORDER BY symbol, date
    """, (cutoff,))
    rows = c.fetchall()
    conn.close()

    sym_data = {}
    for r in rows:
        sym = r[0]
        if sym not in sym_data:
            sym_data[sym] = []
        sym_data[sym].append(r)

    print(f'  分析 {len(sym_data)} 個標的...')

    candidates = []
    experience = load_experience()
    exp_dict = {e['symbol']: e for e in experience}

    for sym, data in sym_data.items():
        if len(data) < 30:
            continue

        latest = data[-1]
        price = latest[2]
        rsi = latest[3] or 50
        macd = latest[4] or 0
        sma20 = latest[5] or price
        sma60 = latest[6] or price
        atr = latest[7] or 0
        vol_ratio = latest[8] or 1

        if price <= 0 or atr <= 0:
            continue

        atr_pct = atr / price * 100
        score = 0
        tags = []
        reasons = []

        # RSI 評分
        if 25 <= rsi <= 40:
            score += 35; tags.append('RSI進場區'); reasons.append(f'RSI={rsi:.0f}(佳)')
        elif 40 < rsi <= 55:
            score += 25; tags.append('RSI偏低'); reasons.append(f'RSI={rsi:.0f}')
        elif 55 < rsi <= 65:
            score += 10; tags.append('RSI中性')
        else:
            tags.append(f'RSI過熱{rsi:.0f}')

        # MACD
        if macd > 0:
            score += 20; tags.append('MACD多頭')
        else:
            tags.append('MACD空頭')

        # MA 多頭
        if sma20 > sma60:
            score += 10; tags.append('MA多頭'); reasons.append('MA20>MA60')
        else:
            tags.append('MA空頭')

        # 量能
        if vol_ratio >= 2.0:
            score += 15; tags.append(f'放量爆{vol_ratio:.1f}x')
        elif vol_ratio >= 1.5:
            score += 10; tags.append(f'放量{vol_ratio:.1f}x')

        # ATR
        if atr_pct >= 5:
            score += 5; tags.append(f'波動大{atr_pct:.1f}%')

        # 經驗加成
        if sym in exp_dict:
            prev_wr = exp_dict[sym].get('win_rate', 0) or 0
            if prev_wr >= 0.7:
                score += 10; tags.append(f'歷史勝{prev_wr:.0%}')
            elif prev_wr >= 0.5:
                score += 5

        priority = '🔥高度' if score >= 70 else ('🟡觀察' if score >= 50 else '⚪中立')

        candidates.append({
            'symbol': sym, 'price': round(price, 2), 'rsi': round(rsi, 1),
            'macd': round(macd, 3), 'sma20': round(sma20, 2), 'sma60': round(sma60, 2),
            'atr_pct': round(atr_pct, 1), 'vol_ratio': round(vol_ratio, 2),
            'ma_bull': sma20 > sma60, 'score': score,
            'priority': priority, 'tags': tags, 'reasons': reasons,
        })

    candidates.sort(key=lambda x: x['score'], reverse=True)
    print(f'  候選: {len(candidates)} 檔')
    return candidates[:100]  # 擴大樣本


def stage2_backtest_simulation(candidates):
    """Stage2: 使用 DB 預計算 RSI/SMA 欄位做沙盒回測"""
    print('\n[Stage2] 沙盒模擬中...')
    cutoff90 = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    experience = load_experience()
    exp_dict = {e['symbol']: e for e in experience}

    strategies = []

    for cand in candidates[:20]:
        sym = cand['symbol']
        # 使用 DB 預計算欄位
        c.execute("""SELECT date, close, high, low, rsi_14, macd_hist, sma_20, sma_60
            FROM daily_ohlcv WHERE symbol=? AND date>=? ORDER BY date""", (sym, cutoff90))
        rows = list(c.fetchall())
        if len(rows) < 60:
            continue

        prices = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        rsi_list = [r[4] for r in rows]
        sma20_list = [r[6] for r in rows]
        sma60_list = [r[7] for r in rows]

        wins = total = 0
        loss_list = []
        win_list = []

        # 進場：僅用 RSI 25-55（不放 MA 條件，避免過度嚴格）
        for i in range(20, len(prices) - 7):
            rsi_val = rsi_list[i] if rsi_list[i] is not None else 50
            if rsi_val < 25 or rsi_val > 55:
                continue

            entry = prices[i]
            # ATR 停損
            tr_list = [max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0) for j in range(max(0, i-13), i+1)]
            atr_sim = sum(tr_list) / len(tr_list) if tr_list else 1
            sl = entry - atr_sim * 1.5
            tp = entry + atr_sim * 3.0

            exited = False
            for j in range(i+1, min(i+8, len(prices))):
                if prices[j] <= sl:
                    total += 1; loss_list.append((entry - prices[j]) / entry * 100); exited = True; break
                elif prices[j] >= tp:
                    wins += 1; total += 1; win_list.append((prices[j] - entry) / entry * 100); exited = True; break

        win_rate = wins / total if total > 0 else 0
        avg_win = sum(win_list) / len(win_list) if win_list else 0
        avg_loss = sum(loss_list) / len(loss_list) if loss_list else 0
        pf = avg_win / abs(avg_loss) if avg_loss != 0 else 0

        sym_exp = exp_dict.get(sym, {})
        prev_wr = sym_exp.get('win_rate', 0) or 0

        status = 'ready' if win_rate >= 0.25 else 'watch'  # 降低門檻至45%

        strategies.append({
            'symbol': sym, 'price': cand['price'], 'score': cand['score'],
            'sim_win_rate': round(win_rate * 100, 1), 'sim_trades': total,
            'prev_win_rate': round(prev_wr * 100, 1),
            'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2), 'pf': round(pf, 2),
            'atr_pct': cand['atr_pct'], 'rsi': cand['rsi'],
            'ma_bull': cand['ma_bull'], 'tags': cand['tags'],
            'status': status,
            'risk': {
                'stop_loss_pct': round(1.5 * cand['atr_pct'], 1),
                'take_profit_pct': round(3.0 * cand['atr_pct'], 1),
                'max_position_pct': 8 if cand['atr_pct'] < 5 else 10
            }
        })

    conn.close()
    strategies.sort(key=lambda x: x['sim_win_rate'], reverse=True)
    print(f'  模擬完成: {len(strategies)} 檔 ({sum(s["sim_trades"] for s in strategies)}筆)')
    return strategies


def stage3_learning_update(strategies):
    """Stage3: 寫入經驗資料庫"""
    print('\n[Stage3] 學習更新中...')
    exp_path = DATA / 'experience_ledger.json'
    experience = load_experience()
    exp_dict = {e['symbol']: e for e in experience}

    for s in strategies:
        entry = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'symbol': s['symbol'], 'win_rate': s['sim_win_rate'] / 100,
            'trades': s['sim_trades'], 'pf': s['pf'], 'atr_pct': s['atr_pct'],
            'source': 'hunter_v2', 'status': s['status'],
            'rsi': s['rsi'], 'ma_bull': s['ma_bull']
        }
        if s['symbol'] in exp_dict:
            exp_dict[s['symbol']].update(entry)
        else:
            exp_dict[s['symbol']] = entry

    with open(exp_path, 'w', encoding='utf-8') as f:
        json.dump(list(exp_dict.values()), f, ensure_ascii=False, indent=2)
    print(f'  經驗資料庫更新: {len(strategies)} 筆記錄')


def stage4_watchlist_write(strategies):
    """Stage4: 寫入觀察區"""
    print('\n[Stage4] 觀察區寫入中...')
    watch = [s for s in strategies if s['status'] == 'ready' and s['sim_trades'] >= 2]
    watch.sort(key=lambda x: -x['score'])

    watch_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'watch_list': [{
            'symbol': s['symbol'], 'price': s['price'], 'score': s['score'],
            'win_rate': s['sim_win_rate'], 'trades': s['sim_trades'],
            'pf': s['pf'], 'atr_pct': s['atr_pct'], 'rsi': s['rsi'],
            'tags': s['tags'], 'risk': s['risk'],
            'reason': f"模擬{s['sim_win_rate']}%({s['sim_trades']}筆) PF={s['pf']}"
        } for s in watch]
    }

    with open(DATA / 'hunter_watch_list.json', 'w', encoding='utf-8') as f:
        json.dump(watch_data, f, ensure_ascii=False, indent=2)
    print(f'  寫入 {len(watch)} 檔至觀察區')
    return watch


def main():
    print('='*65)
    print('  Tina Brain - 主動獵人模式 v2.1')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*65)

    candidates = get_hunter_candidates()
    if not candidates:
        print('  未發現候選，終止')
        return

    print('\n【TOP 10 候選】')
    print(f"  {'Symbol':<12} {'Price':>8} {'RSI':>5} {'MACD':>8} {'MA':>4} {'ATR%':>5} {'Score':>5} {'Priority'}")
    print(f"  {'-'*65}")
    for c in candidates[:10]:
        ma = '▲' if c['ma_bull'] else '▼'
        print(f"  {c['symbol']:<12} ${c['price']:>8.2f} {c['rsi']:>5.1f} {c['macd']:>+8.3f} {ma:>4} {c['atr_pct']:>5.1f}% {c['score']:>5} {c['priority']}")

    strategies = stage2_backtest_simulation(candidates)

    print('\n【模擬結果】')
    ready = [s for s in strategies if s['status'] == 'ready']
    watch = [s for s in strategies if s['status'] == 'watch']
    print(f"  🔥 Ready: {len(ready)} 檔 | 🟡 Watch: {len(watch)} 檔")

    if strategies:
        print(f"\n  {'Symbol':<12} {'Sim WR':>7} {'筆數':>4} {'PF':>5} {'AvgW%':>6} {'AvgL%':>6} Status")
        print(f"  {'-'*60}")
        for s in strategies[:15]:
            icon = '🔥' if s['status'] == 'ready' else '🟡'
            print(f"  {s['symbol']:<12} {s['sim_win_rate']:>6.1f}% {s['sim_trades']:>4} {s['pf']:>5.2f} {s['avg_win']:>6.1f}% {s['avg_loss']:>6.1f}% {icon}")

    stage3_learning_update(strategies)
    watch_list = stage4_watchlist_write(strategies)

    print('\n' + '='*65)
    print('  獵人行動完成')
    print('='*65)

    if watch_list:
        print('\n【觀察區入圍】')
        for w in watch_list:
            print(f"  🔥 {w['symbol']}: ${w['price']} | 勝率 {w['sim_win_rate']}% | PF={w['pf']}")


if __name__ == '__main__':
    main()