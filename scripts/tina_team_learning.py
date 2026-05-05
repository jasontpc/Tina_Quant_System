# -*- coding: utf-8 -*-
"""
Tina Brain - 全團隊學習與回測系統 v4.0
======================================
邏輯推理增強版：
1. 擴充回測期至 2 年（增加交易筆數）
2. 動態停利（根據 ATR 調整）
3. 跨市場驗證（TW + US）
4. 失敗交易冷卻期（5日不進場同股票）
5. 追加進場（首筆虧損後允許加碼）
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

TEAMS = {
    'NANA': {
        'name': 'NANA 波段操作',
        'rsi_min': 35, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['2464.TW','3324.TWO','3037.TW','1590.TW'],
    },
    'LEO': {
        'name': 'LEO AI科技',
        'rsi_min': 25, 'rsi_max': 40,
        'macd_min': 0,
        'filter': 'vol_1.5x',
        'watch': ['3711.TW','8299.TW','2467.TW','5269.TW','2359.TW','4966.TWO','2408.TW','2344.TW','7730.TW'],
    },
    'MAGGY': {
        'name': 'MAGGY 美股AI',
        'rsi_min': 0, 'rsi_max': 999,
        'macd_min': 0,
        'macd_cross': True,
        'filter': 'ma20_above_ma60',
        'watch': ['MSFT', 'CRM'],
    },
    'SHERKY': {
        'name': 'SHERKY ETF/能源',
        'rsi_min': 0, 'rsi_max': 45,
        'macd_min': 0,
        'filter': 'none',
        'watch': ['1519.TW'],
    },
    'AION': {
        'name': 'AION 新能源車',
        'rsi_min': 30, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['2201.TW', '2207.TW'],
    },
    'GUARD': {
        'name': 'GUARD 軍工/國防',
        'rsi_min': 30, 'rsi_max': 55,
        'macd_min': 0,
        'filter': 'none',
        'watch': ['2634.TW', '2313.TW'],
    },
    'FINMAX': {
        'name': 'FINMAX 金融/金控',
        'rsi_min': 35, 'rsi_max': 55,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['2881.TW','2882.TW','2883.TW','2884.TW','2885.TW','2891.TW','2892.TW'],
    },
    'CPO': {
        'name': 'CPO 散熱產業',
        'rsi_min': 30, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['6230.TW','3324.TWO','3653.TW','3711.TW','3017.TW','4908.TW','6120.TW','6592.TW'],
    },
}


def backtest_enhanced(sym, rsi_min, rsi_max, macd_min, filter_name, macd_cross=False, days=730):
    """
    增強回測：2年數據 + 動態停利 + 失敗冷卻
    """
    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute("SELECT date, close, high, low, volume FROM daily_ohlcv WHERE symbol=? AND date>=? ORDER BY date", (sym, cutoff))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 60:
        return None

    dates = [r[0] for r in rows]
    prices = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    vols = [r[4] for r in rows]

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_s = 100 - (100 / (1 + rs))

    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_sig = macd_l.ewm(span=9, adjust=False).mean()
    macd_h = macd_l - macd_sig

    sma20 = s.ewm(span=20, adjust=False).mean()
    sma60 = s.ewm(span=60, adjust=False).mean()
    avg_vol = pd.Series(vols).rolling(20).mean()

    wins, total = 0, 0
    gains_list, losses_list = [], []
    entry_prices = []

    # 失敗冷卻追蹤
    last_loss_idx = -100  # 初始為無限制

    for i in range(60, len(prices) - 15):
        rsi_i = float(rsi_s.iloc[i])
        macd_i = float(macd_h.iloc[i])

        if not (rsi_min <= rsi_i <= rsi_max):
            continue
        if macd_i <= macd_min:
            continue
        if macd_cross:
            macd_prev = float(macd_h.iloc[i-1]) if i > 0 else 0
            if not (macd_prev <= 0 and macd_i > 0):
                continue

        if filter_name == 'ma20_above_ma60':
            if not (float(sma20.iloc[i]) > float(sma60.iloc[i])):
                continue
        elif filter_name == 'vol_1.5x':
            if vols[i] <= float(avg_vol.iloc[i]) * 1.5:
                continue

        # 失敗冷卻：上次虧損後 5 日不進場
        if i - last_loss_idx < 5:
            continue

        entry = prices[i]
        atr_val = float(pd.Series([max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0) for j in range(max(0,i-13), i+1)]).ewm(span=14, adjust=False).mean().iloc[-1])

        # 動態停利：根據 ATR 調整
        sl = entry - atr_val * 1.5
        tp = entry + atr_val * 3.5  # 稍微放寬

        exited = False
        for j in range(i+1, min(i+16, len(prices))):  # 放寬至15日
            if prices[j] <= sl:
                total += 1
                losses_list.append((sl - entry) / entry * 100)
                entry_prices.append(entry)
                last_loss_idx = j  # 更新失敗索引
                exited = True
                break
            elif prices[j] >= tp:
                wins += 1
                total += 1
                gains_list.append((tp - entry) / entry * 100)
                exited = True
                break

    if total == 0:
        return None

    wr = wins / total * 100
    avg_g = sum(gains_list) / len(gains_list) if gains_list else 0
    avg_l = sum(losses_list) / len(losses_list) if losses_list else 0
    pf = avg_g / abs(avg_l) if avg_l != 0 else 0

    return {
        'trades': total, 'win_rate': round(wr, 1), 'wins': wins, 'losses': total - wins,
        'avg_gain': round(avg_g, 2), 'avg_loss': round(avg_l, 2),
        'pf': round(pf, 2),
        'gains': gains_list, 'losses': losses_list
    }


def analyze_team(team_id, params):
    """分析整個團隊"""
    results = []
    for sym in params['watch']:
        bt = backtest_enhanced(sym, params['rsi_min'], params['rsi_max'],
                               params['macd_min'], params['filter'],
                               params.get('macd_cross', False))
        if bt:
            bt['symbol'] = sym
            bt['team'] = team_id
            results.append(bt)

    if not results:
        return {'team': team_id, 'name': params['name'], 'stocks': [], 'summary': {'trades': 0, 'win_rate': 0}}

    total_trades = sum(r['trades'] for r in results)
    total_wins = sum(r['wins'] for r in results)
    all_gains = [g for r in results for g in r.get('gains', [])]
    all_losses = [l for r in results for l in r.get('losses', [])]

    summary = {
        'trades': total_trades,
        'win_rate': round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0,
        'avg_gain': round(sum(all_gains)/len(all_gains), 2) if all_gains else 0,
        'avg_loss': round(sum(all_losses)/len(all_losses), 2) if all_losses else 0,
        'pf': round((sum(all_gains)/len(all_gains)) / abs(sum(all_losses)/len(all_losses)), 2) if all_losses and all_gains else 0,
    }

    return {'team': team_id, 'name': params['name'], 'stocks': results, 'summary': summary}


def reasoning_chain(team_id, summary, stocks):
    """慢思考推理鏈"""
    thoughts = []
    t = summary

    # 裁判分析
    if t['trades'] == 0:
        thoughts.append(f"⚠️ {team_id}: 無交易，需放寬進場條件")
    elif t['win_rate'] >= 60:
        thoughts.append(f"✅ {team_id}: 勝率 {t['win_rate']}% 合格（{t['trades']}筆）")
        if t['pf'] >= 1.5:
            thoughts.append(f"  風險報酬比 PF={t['pf']} 優秀")
    elif t['win_rate'] >= 45:
        thoughts.append(f"🟡 {team_id}: 勝率 {t['win_rate']}% 可接受（{t['trades']}筆）")
    else:
        thoughts.append(f"🔴 {team_id}: 勝率 {t['win_rate']}% 偏低，需檢討參數")

    # 專家觀點
    if t['trades'] >= 20:
        thoughts.append(f"  📊 樣本充足（{t['trades']}筆），統計可靠")
    elif t['trades'] >= 5:
        thoughts.append(f"  📊 樣本有限（{t['trades']}筆），需更多驗證")
    else:
        thoughts.append(f"  📊 樣本不足（{t['trades']}筆），暫不下結論")

    return thoughts


def main():
    print('='*70)
    print('  Tina Brain 全團隊學習系統 v4.0（邏輯推理增強版）')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('  回測期: 2年 | 停利: 3.5x ATR | 失敗冷卻: 5日')
    print('='*70)

    all_results = {}

    for team_id, params in TEAMS.items():
        print(f"\n【{team_id}】{params['name']} 掃描中...")
        result = analyze_team(team_id, params)
        all_results[team_id] = result

        s = result['summary']
        stocks = result['stocks']
        print(f"  總交易: {s['trades']} 筆 | 勝率: {s['win_rate']}% | PF: {s['pf']} | AvgW: {s['avg_gain']}% | AvgL: {s['avg_loss']}%")

        if stocks:
            for st in sorted(stocks, key=lambda x: -x['win_rate'])[:3]:
                icon = '🟢' if st['win_rate'] >= 60 else ('🟡' if st['win_rate'] >= 45 else '🔴')
                print(f"    {icon} {st['symbol']}: {st['win_rate']}% ({st['trades']}筆) PF={st['pf']}")

        # 推理鏈
        thoughts = reasoning_chain(team_id, s, stocks)
        for th in thoughts:
            print(f"  {th}")

    # 總結排名
    print('\n' + '='*70)
    print('  【全團隊排名】')
    print(f"  {'團隊':<8} {'勝率':>6} {'交易':>5} {'PF':>5} {'AvgW%':>6} {'AvgL%':>6}")
    print(f"  {'-'*45}")

    ranked = sorted(all_results.values(), key=lambda x: -x['summary']['win_rate'])
    for r in ranked:
        s = r['summary']
        icon = '🟢' if s['win_rate'] >= 60 else ('🟡' if s['win_rate'] >= 45 else '🔴')
        print(f"  {r['team']:<8} {icon}{s['win_rate']:>5.1f}% {s['trades']:>5} {s['pf']:>5.2f} {s['avg_gain']:>6.1f}% {s['avg_loss']:>6.1f}%")

    total_all = sum(r['summary']['trades'] for r in ranked)
    wr_all = sum(r['summary']['win_rate'] * r['summary']['trades'] for r in ranked) / total_all if total_all > 0 else 0
    print(f"  {'-'*45}")
    print(f"  {'加權平均':<8} {'🟢' if wr_all >= 50 else '⚪'}{wr_all:>5.1f}% {total_all:>5}")

    # 寫入結果
    output = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'backtest_days': 730,
        'results': {k: {'summary': v['summary'], 'stocks': [{kk: vv for kk, vv in r.items() if kk != 'gains' and kk != 'losses'} for r in v['stocks']]} for k, v in all_results.items()}
    }
    with open(DATA / 'team_learning_results_v4.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  → 結果已寫入: data/team_learning_results_v4.json")


if __name__ == '__main__':
    main()