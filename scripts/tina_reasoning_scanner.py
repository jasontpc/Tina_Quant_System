# -*- coding: utf-8 -*-
"""
Enhanced entry scanner using reasoning engine
==========================================
Uses the 5 reasoning mechanisms to find more trade opportunities
"""
import sqlite3, json, sys, yfinance
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
sys.path.insert(0, str(WORKSPACE / "scripts"))

from tina_reasoning_engine import (
    ExpertCommittee, detect_contradictions, tag_market_event,
    stress_test, dynamic_stop_loss
)


def get_live_indicators(sym):
    """Get live indicators for a symbol"""
    try:
        tk = yfinance.Ticker(sym)
        h = tk.history(period='90d')
        if len(h) < 30:
            return None

        prices = list(h['Close'])
        highs = list(h['High'])
        lows = list(h['Low'])
        vols = list(h['Volume'])

        s = pd.Series(prices)

        # RSI
        delta = s.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema12 = s.ewm(span=12, adjust=False).mean()
        ema26 = s.ewm(span=26, adjust=False).mean()
        macd_l = ema12 - ema26
        macd_s = macd_l.ewm(span=9, adjust=False).mean()
        macd_h = macd_l - macd_s

        # SMA
        sma20 = s.ewm(span=20, adjust=False).mean()
        sma60 = s.ewm(span=60, adjust=False).mean()

        # ATR
        tr = pd.Series([max(highs[i]-lows[i], abs(highs[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))])
        atr = tr.ewm(span=14, adjust=False).mean()

        # Vol ratio
        vol20 = pd.Series(vols).rolling(20).mean()
        vol_r = vols[-1] / vol20.iloc[-1] if vol20.iloc[-1] > 0 else 1.0

        # Price change
        price_change_5d = (prices[-1] / prices[-6] - 1) * 100 if len(prices) >= 6 else 0
        price_change_20d = (prices[-1] / prices[-21] - 1) * 100 if len(prices) >= 21 else 0

        return {
            'rsi': float(rsi.iloc[-1]),
            'rsi_prev': float(rsi.iloc[-2]) if len(rsi) > 1 else float(rsi.iloc[-1]),
            'macd_hist': float(macd_h.iloc[-1]),
            'macd_hist_prev': float(macd_h.iloc[-2]) if len(macd_h) > 1 else float(macd_h.iloc[-1]),
            'vol_ratio': vol_r,
            'price': prices[-1],
            'sma20': float(sma20.iloc[-1]),
            'sma60': float(sma60.iloc[-1]),
            'atr_pct': float(atr.iloc[-1] / prices[-1] * 100),
            'price_change_5d': price_change_5d,
            'price_change_20d': price_change_20d,
            'high_52w': max(highs),
        }
    except:
        return None


def scan_with_reasoning(symbols, team_config):
    """Scan symbols using reasoning engine"""
    results = []

    for sym in symbols:
        ind = get_live_indicators(sym)
        if not ind:
            continue

        rsi = ind['rsi']
        macd = ind['macd_hist']
        vol_r = ind['vol_ratio']
        price = ind['price']
        sma20 = ind['sma20']
        sma60 = ind['sma60']
        atr_pct = ind['atr_pct']
        price_change = ind['price_change_5d']
        rsi_change = rsi - ind['rsi_prev']
        macd_change = macd - ind['macd_hist_prev']

        indicators = {
            'rsi': rsi,
            'macd_hist': macd,
            'vol_ratio': vol_r,
            'price': price,
            'sma20': sma20,
            'sma60': sma60,
            'atr_pct': atr_pct,
            'price_change': price_change,
            'rsi_change': rsi_change,
            'macd_change': macd_change,
            'institutional': '',
            'high_52w': ind['high_52w'],
        }

        # Expert committee debate
        committee = ExpertCommittee(sym, indicators)
        verdict, action, debate_log = committee.debate()

        # Tag market events
        tags = tag_market_event(vol_r, price_change, rsi_change, macd_change)

        # Stress test
        stress = stress_test(price, atr_pct, 1.0)

        # Detect contradictions
        contradictions = detect_contradictions(rsi, macd, vol_r, '', price_change > 0 and 'up' or 'down')

        # === 評分邏輯（推理增強，放寬進場區間）===
        score = 0
        entry_signal = 'no_signal'

        # BULL 判斷 + 韌性測試
        if verdict == 'BULL' and stress['resilience_score'] >= 65:
            score += 40

        # RSI 評分：放寬至 25-55（根據 v4 回測驗證）
        if 25 <= rsi <= 40:
            score += 30; tags.append('RSI進場區')
        elif 40 < rsi <= 55:
            score += 20; tags.append('RSI偏低')
        elif 55 < rsi <= 65:
            score += 10; tags.append('RSI中性')

        # MACD 多頭
        if macd > 0:
            score += 15; tags.append('MACD多頭')

        # MA 多頭確認（加分項，不扣分）
        if sma20 > sma60:
            score += 8; tags.append('MA多頭')

        # 量能放大
        if vol_r > 2.0:
            score += 15; tags.append(f'放量爆{vol_r:.1f}x')
        elif vol_r > 1.5:
            score += 10; tags.append(f'放量{vol_r:.1f}x')
        elif vol_r > 1.2:
            score += 5; tags.append(f'溫和放量{vol_r:.1f}x')

        # 事件標註加成
        if 'VOLUME_SPIKE_PUMP' in tags:
            score += 10
        if 'MOMENTUM_BREAKOUT' in tags:
            score += 8

        # 矛盾扣分
        if contradictions:
            score -= 15

        # RSI 動量方向確認（避免逆勢）
        if rsi_change < -5 and macd_change > 0:
            score += 10; tags.append('RSI回調確認')

        # === 進場訊號門檻（根據2年回測動態調整）===
        if score >= 40:
            entry_signal = 'buy'
        elif score >= 25 and stress['resilience_score'] >= 60:
            entry_signal = 'watch'
        elif score >= 20 and rsi < 40 and macd > 0:
            entry_signal = 'watch'  # 特別放寬超賣進場

        results.append({
            'symbol': sym,
            'verdict': verdict,
            'score': score,
            'signal': entry_signal,
            'rsi': round(rsi, 1),
            'macd': round(macd, 3),
            'vol_r': round(vol_r, 2),
            'resilience': stress['resilience_score'],
            'tags': tags,
            'contradictions': len(contradictions),
            'price': price,
            'atr_pct': round(atr_pct, 1),
        })

    return results


def main():
    print('='*70)
    print('  Tina Brain - 推理增強掃描系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    # Team watch lists (all 8 teams)
    teams = {
        'LEO': ['5269.TW', '4966.TWO', '2359.TW', '3711.TW', '8299.TW', '2467.TW', '2408.TW', '2344.TW', '7730.TW'],
        'NANA': ['2464.TW', '3324.TWO', '3037.TW', '1590.TW'],
        'GUARD': ['2634.TW', '2313.TW'],
        'AION': ['2201.TW', '2207.TW'],
        'FINMAX': ['2881.TW', '2882.TW', '2883.TW', '2884.TW', '2885.TW', '2891.TW', '2892.TW'],
        'MAGGY': ['MSFT', 'CRM'],
        'SHERKY': ['1519.TW'],
        'CPO': ['6230.TW', '3324.TWO', '3653.TW', '3711.TW', '3017.TW', '4908.TW', '6120.TW', '6592.TW'],
    }

    all_signals = []

    for team, syms in teams.items():
        print(f'\n【{team}】')
        scan_results = scan_with_reasoning(syms, {})

        buy_signals = [r for r in scan_results if r['signal'] == 'buy']
        watch_signals = [r for r in scan_results if r['signal'] == 'watch']

        for r in scan_results:
            sig = r['signal'].upper()
            sig_marker = '🟢' if sig == 'BUY' else ('🟡' if sig == 'WATCH' else '⚪')
            print(f"  {sig_marker} {r['symbol']}: {r['verdict']} Score={r['score']} RSI={r['rsi']} MACD={r['macd']} Vol={r['vol_r']}x Resil={r['resilience']}%")

        if buy_signals:
            print(f"  → 進場訊號: {len(buy_signals)} 檔")
            all_signals.extend(buy_signals)
        else:
            print(f"  → 無進場訊號")

    if all_signals:
        print()
        print('='*70)
        print('【全部進場訊號】')
        for s in sorted(all_signals, key=lambda x: -x['score']):
            print(f"  🟢 {s['symbol']}: Score={s['score']} RSI={s['rsi']} Vol={s['vol_r']}x Resil={s['resilience']}% Tags={str(s['tags'])[:60]}")
    else:
        print()
        print('  今日無進場訊號（觀望）')


if __name__ == '__main__':
    main()