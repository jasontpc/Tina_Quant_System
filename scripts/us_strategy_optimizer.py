# -*- coding: utf-8 -*-
"""
US Strategy Optimizer — Tina Quant System
針對完全通過篩選的 4 檔股票建立並維護專屬策略
也包含 Top 10 候選個股的策略建議
"""

import sqlite3
import json
import os
import yfinance as yf
import pandas as pd
import math
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_JSON = os.path.join(DATA_DIR, 'us_stocks_alerts.json')
DB_PATH = os.path.join(DATA_DIR, 'us_value_growth.db')
STRATEGY_JSON = os.path.join(DATA_DIR, 'us_strategy_config.json')

# ── Core 4 stocks strategy ────────────────────────────────────────────────────
CORE_STRATEGIES = {
    'D': {
        'name': 'Dominion Energy',
        'style': 'utility_income',
        'ideal_rsi_entry': 60,
        'ideal_rsi_entry_min': 30,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.08,
        'profit_target_pct': 0.15,
        'atr_stop_pct': 0.05,
        'profit_target_atr': 3.0,
        'ma_entry': 'below_ma20',
        'div_yield_target': 4.0,
        'pe_fair': 18,
        'pe_undervalued': 14,
        'notes': '公用/收息型：4%股息+資本利得，防守優先',
        'entry_rationale': 'RSI < 60 + MA20 below price + div yield > 3.5%',
        'exit_strategy': 'ATR吊燈停利 or 目標價觸發'
    },
    'BMY': {
        'name': 'Bristol-Myers Squibb',
        'style': 'pharma_value',
        'ideal_rsi_entry': 55,
        'ideal_rsi_entry_min': 30,
        'ideal_rsi_max': 65,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.18,
        'atr_stop_pct': 0.06,
        'profit_target_atr': 3.5,
        'ma_entry': 'below_ma60',
        'div_yield_target': 4.0,
        'pe_fair': 17,
        'pe_undervalued': 14,
        'notes': '醫藥/價值型：PE 14-17 進場，價值回歸',
        'entry_rationale': 'RSI < 55 + PE < 17 + below MA60',
        'exit_strategy': 'PE達18+ or ATR 3.5x 停利'
    },
    'SO': {
        'name': 'Southern Company',
        'style': 'utility_income',
        'ideal_rsi_entry': 58,
        'ideal_rsi_entry_min': 30,
        'ideal_rsi_max': 68,
        'stop_loss_pct': 0.07,
        'profit_target_pct': 0.14,
        'atr_stop_pct': 0.05,
        'profit_target_atr': 2.8,
        'ma_entry': 'below_ma20',
        'div_yield_target': 3.0,
        'pe_fair': 20,
        'pe_undervalued': 16,
        'notes': '公用/收益型：3%+股息目標，穩定收益',
        'entry_rationale': 'RSI < 58 + div yield > 3% + MA aligned',
        'exit_strategy': '目標價或ATR 2.8x 停利'
    },
    'DXCM': {
        'name': 'DexCom',
        'style': 'medtech_growth',
        'ideal_rsi_entry_min': 40,
        'ideal_rsi_entry_max': 50,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.12,
        'profit_target_pct': 0.25,
        'atr_stop_pct': 0.08,
        'profit_target_atr': 4.0,
        'ma_entry': 'rsi_reversal',
        'div_yield_target': 0,
        'pe_fair': 30,
        'pe_undervalued': 25,
        'notes': '醫療/成長型：RSI 40-50 進場甜區，成長反彈',
        'entry_rationale': 'RSI 40-50 zone + momentum reversal',
        'exit_strategy': 'ATR 4x 吊燈 or 25%目標'
    }
}

# ── Top 10 candidates strategy ──────────────────────────────────────────────────
TOP10_STRATEGIES = {
    'FITB': {
        'name': 'First Internet Bancorp',
        'style': 'bank_value',
        'ideal_rsi_entry': 60,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.15,
        'atr_stop_pct': 0.06,
        'notes': '銀行價值型：MA 多頭，目標 +15%',
        'price_reference': 50.64,
        'rsi_reference': 59.2
    },
    'HBAN': {
        'name': 'Huntington Bancshares',
        'style': 'regional_bank',
        'ideal_rsi_entry': 58,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.18,
        'atr_stop_pct': 0.06,
        'notes': '區域銀行：低估區間，目標 +18%',
        'price_reference': 16.67,
        'rsi_reference': 54.5
    },
    'CARG': {
        'name': 'CarGurus',
        'style': 'tech_growth',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.12,
        'profit_target_pct': 0.20,
        'atr_stop_pct': 0.08,
        'notes': '科技成長型：高成長但波動大'
    },
    'NEE': {
        'name': 'NextEra Energy',
        'style': 'utility_income',
        'ideal_rsi_entry': 58,
        'ideal_rsi_max': 68,
        'stop_loss_pct': 0.08,
        'profit_target_pct': 0.15,
        'atr_stop_pct': 0.05,
        'notes': '公用/潔淨能源：穩定收益+成長'
    },
    'SWKS': {
        'name': 'Skyworks Solutions',
        'style': 'semi_value',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 65,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.18,
        'atr_stop_pct': 0.06,
        'notes': '半導體價值型：RF技術，目標+18%'
    },
    'CVLT': {
        'name': 'Commvault Systems',
        'style': 'tech_growth',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.12,
        'profit_target_pct': 0.22,
        'atr_stop_pct': 0.08,
        'notes': '資料管理軟體：高成長雲端'
    },
    'SCHW': {
        'name': 'Charles Schwab',
        'style': 'broker_value',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 65,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.20,
        'atr_stop_pct': 0.06,
        'notes': '券商價值股：進場甜區，目標+20%',
        'price_reference': 92.42,
        'rsi_reference': 48.3
    },
    'SLB': {
        'name': 'Schlumberger',
        'style': 'energy_services',
        'ideal_rsi_entry': 60,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.10,
        'profit_target_pct': 0.18,
        'atr_stop_pct': 0.06,
        'notes': '能源服務：景氣循環型，目標+18%'
    },
    'NET': {
        'name': 'Cloudflare',
        'style': 'cloud_growth',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.12,
        'profit_target_pct': 0.22,
        'atr_stop_pct': 0.08,
        'notes': '雲端/網安：高成長，目標+22%'
    },
    'MU': {
        'name': 'Micron Technology',
        'style': 'semi_growth',
        'ideal_rsi_entry': 55,
        'ideal_rsi_max': 70,
        'stop_loss_pct': 0.12,
        'profit_target_pct': 0.20,
        'atr_stop_pct': 0.08,
        'notes': '記憶體：景氣循環+AI需求'
    }
}

# ── Alert thresholds ──────────────────────────────────────────────────────────
ALERT_THRESHOLDS = {
    'D':        {'rsi_overbought': 70, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'BMY':      {'rsi_overbought': 65, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'SO':       {'rsi_overbought': 68, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'DXCM':     {'rsi_overbought': 70, 'rsi_oversold': 35, 'pos_52w_alert': 0.90, 'bias20_alert': 15},
    'FITB':     {'rsi_overbought': 70, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'HBAN':     {'rsi_overbought': 70, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'SCHW':     {'rsi_overbought': 65, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12},
    'default':  {'rsi_overbought': 70, 'rsi_oversold': 30, 'pos_52w_alert': 0.85, 'bias20_alert': 12}
}

# ── Calculate ATR ──────────────────────────────────────────────────────────────
def calc_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period

# ── Check alerts for a symbol ─────────────────────────────────────────────────
def check_alerts(symbol, data):
    thresh = ALERT_THRESHOLDS.get(symbol, ALERT_THRESHOLDS['default'])
    alerts = []
    rsi = data.get('rsi_14')
    pos52 = data.get('pos_52w')
    bias20 = data.get('bias20')
    price = data.get('price')

    if rsi and rsi >= thresh['rsi_overbought']:
        alerts.append(f'⚠️ RSI Overbought: {rsi:.1f} (>{thresh["rsi_overbought"]})')
    if rsi and rsi <= thresh['rsi_oversold']:
        alerts.append(f'✅ RSI Oversold: {rsi:.1f} (<{thresh["rsi_oversold"]}) - Entry zone!')
    if pos52 and pos52 >= thresh['pos_52w_alert']:
        alerts.append(f'⚠️ 52W Position High: {pos52*100:.1f}%')
    if bias20 and abs(bias20) >= thresh['bias20_alert']:
        alerts.append(f'⚠️ BIAS20 Extended: {bias20:+.1f}%')

    return alerts

# ── Analyze a stock & return entry/exit signals ────────────────────────────────
def analyze_stock(symbol, strategy=None):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='2y')
        if h.empty or len(h) < 60:
            return None
        info = t.info or {}
        closes = h['Close'].tolist()
        highs = h['High'].tolist()
        lows = h['Low'].tolist()
        volumes = h['Volume'].tolist()
        price = closes[-1]

        # RSI
        deltas = pd.Series(closes).diff()
        gain = deltas.where(deltas > 0, 0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        loss = (-deltas.where(deltas < 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = gain / loss
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])

        rsi_30_deltas = pd.Series(closes).diff()
        rsi_30_gain = rsi_30_deltas.where(rsi_30_deltas > 0, 0).ewm(alpha=1/30, min_periods=30, adjust=False).mean()
        rsi_30_loss = (-rsi_30_deltas.where(rsi_30_deltas < 0, 0)).ewm(alpha=1/30, min_periods=30, adjust=False).mean()
        rsi_30_rs = rsi_30_gain / rsi_30_loss
        rsi_30 = float((100 - (100 / (1 + rsi_30_rs))).iloc[-1])

        # MAs
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        bias20 = (price / ma20 - 1) * 100
        bias5 = (price / ma5 - 1) * 100

        # ATR
        atr = calc_atr(highs, lows, closes, 14)

        # 52w
        high52 = max(closes[-252:]) if len(closes) >= 252 else max(closes)
        low52 = min(closes[-252:]) if len(closes) >= 252 else min(closes)
        pos52 = (price - low52) / (high52 - low52) if high52 != low52 else 0.5

        # MA alignment
        if price > ma5 > ma20 > ma60:
            ma_align = 'P>MA5>MA20>MA60'
        elif price > ma5 > ma20:
            ma_align = 'P>MA5>MA20'
        elif price > ma5:
            ma_align = 'P>MA5'
        else:
            ma_align = 'BELOW_MA5'

        # Fundamentals
        pe = info.get('trailingPE', 0) or 0
        div_yield = info.get('dividendYield', 0) or 0
        if div_yield > 1:
            div_yield /= 100
        rev_growth = info.get('revenueGrowth', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0

        # Entry signal
        entry_signal = None
        entry_zone = None
        if strategy:
            style = strategy.get('style', 'growth')
            if style == 'medtech_growth':
                rsi_low = strategy.get('ideal_rsi_entry_min', 40)
                rsi_high = strategy.get('ideal_rsi_entry_max', 50)
                if rsi_low <= rsi_14 <= rsi_high:
                    entry_signal = 'BUY'
                    entry_zone = f'RSI {rsi_low}-{rsi_high} zone'
                elif rsi_14 < rsi_low:
                    entry_signal = 'STRONG_BUY'
                    entry_zone = 'Deep oversold - reversal setup'
                elif rsi_14 > strategy.get('ideal_rsi_max', 70):
                    entry_signal = 'OVERBOUGHT'
                    entry_zone = 'Above ideal RSI'
            else:
                rsi_max = strategy.get('ideal_rsi_entry', 60)
                if rsi_14 <= rsi_max:
                    entry_signal = 'BUY'
                    entry_zone = f'RSI < {rsi_max}'
                elif rsi_14 <= 45:
                    entry_signal = 'STRONG_BUY'
                    entry_zone = 'RSI < 45 - strong entry'
                elif rsi_14 > strategy.get('ideal_rsi_max', 70):
                    entry_signal = 'OVERBOUGHT'
                    entry_zone = 'Above ideal RSI max'
                else:
                    entry_signal = 'HOLD'
                    entry_zone = f'RSI {rsi_14:.1f} - neutral'

        # Entry / exit prices
        stop_loss = None
        profit_target = None
        if strategy:
            sl_pct = strategy.get('stop_loss_pct', 0.08)
            pt_pct = strategy.get('profit_target_pct', 0.15)
            if atr:
                stop_loss = price * (1 - strategy.get('atr_stop_pct', 0.05))
                profit_target = price + atr * strategy.get('profit_target_atr', 3.0)
            else:
                stop_loss = price * (1 - sl_pct)
                profit_target = price * (1 + pt_pct)

        return {
            'symbol': symbol,
            'name': info.get('longName', '') or info.get('shortName', '') or symbol,
            'price': price,
            'rsi_14': rsi_14,
            'rsi_30': rsi_30,
            'ma5': ma5, 'ma20': ma20, 'ma60': ma60,
            'bias20': bias20, 'bias5': bias5,
            'atr': atr,
            'high52': high52, 'low52': low52, 'pos52w': pos52,
            'ma_align': ma_align,
            'pe': pe, 'div_yield': div_yield, 'rev_growth': rev_growth, 'roe': roe,
            'entry_signal': entry_signal,
            'entry_zone': entry_zone,
            'stop_loss': stop_loss,
            'profit_target': profit_target,
            'risk_reward': (profit_target - price) / (price - stop_loss) if stop_loss and stop_loss < price else None,
            'strategy': strategy
        }
    except Exception as e:
        print(f'  [ERROR] analyze_stock {symbol}: {e}')
        return None

# ── Build alert config JSON ─────────────────────────────────────────────────────
def build_alert_config():
    config = {
        'version': '1.0',
        'description': 'US Stock Alert Configuration - Tina Quant System',
        'alert_symbols': list(CORE_STRATEGIES.keys()) + list(TOP10_STRATEGIES.keys()),
        'core_symbols': list(CORE_STRATEGIES.keys()),
        'top10_symbols': list(TOP10_STRATEGIES.keys()),
        'stocks': {},
        'alert_thresholds': ALERT_THRESHOLDS
    }
    for sym, strat in {**CORE_STRATEGIES, **TOP10_STRATEGIES}.items():
        config['stocks'][sym] = {
            'name': strat.get('name', sym),
            'style': strat.get('style', 'unknown'),
            'stop_loss_pct': strat.get('stop_loss_pct', 0.10),
            'profit_target_pct': strat.get('profit_target_pct', 0.15),
            'ideal_rsi_entry': strat.get('ideal_rsi_entry', 60),
            'ideal_rsi_entry_min': strat.get('ideal_rsi_entry_min', 30),
            'ideal_rsi_max': strat.get('ideal_rsi_max', 70),
            'atr_stop_pct': strat.get('atr_stop_pct', 0.06),
            'profit_target_atr': strat.get('profit_target_atr', 3.0),
            'notes': strat.get('notes', ''),
            'entry_rationale': strat.get('entry_rationale', ''),
            'exit_strategy': strat.get('exit_strategy', '')
        }
    return config

# ── Build strategy JSON ────────────────────────────────────────────────────────
def build_strategy_json():
    return {
        'version': '1.0',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'core_strategies': CORE_STRATEGIES,
        'top10_strategies': TOP10_STRATEGIES
    }

# ── Build Telegram report ───────────────────────────────────────────────────────
def build_report(results):
    lines = []
    lines.append('📊 *US Stock Strategy Report*')
    lines.append(f'__{datetime.now().strftime("%Y-%m-%d %H:%M")}__')
    lines.append('')

    # Core 4
    core_syms = list(CORE_STRATEGIES.keys())
    core_results = [r for r in results if r and r['symbol'] in core_syms]
    if core_results:
        lines.append('🎯 *Core 4 — 完全通過篩選*')
        lines.append('')
        for r in core_results:
            sig = r['entry_signal'] or 'N/A'
            sig_emoji = {'STRONG_BUY': '🟢🟢', 'BUY': '🟢', 'HOLD': '🟡', 'OVERBOUGHT': '🔴'}.get(sig, '⚪')
            lines.append(f'{sig_emoji} *{r["symbol"]}* — {r["name"]}')
            lines.append(f'  💰 ${r["price"]:.2f} | RSI(14)={r["rsi_14"]:.1f} | RSI(30)={r["rsi_30"]:.1f}')
            lines.append(f'  📐 MA: MA5=${r["ma5"]:.2f} MA20=${r["ma20"]:.2f} MA60=${r["ma60"]:.2f}')
            lines.append(f'  📊 BIAS20={r["bias20"]:+.1f}% | 52W: {r["pos52w"]*100:.1f}% ({r["low52"]:.2f}–{r["high52"]:.2f})')
            lines.append(f'  🎯 Entry: *{r["entry_signal"]}* ({r["entry_zone"]})')
            if r['stop_loss']:
                lines.append(f'  🛡 SL: ${r["stop_loss"]:.2f} | TP: ${r["profit_target"]:.2f}')
                rr = r['risk_reward']
                lines.append(f'  📐 R/R: {rr:.2f}x' if rr else '')
            # fundamentals
            pe = r['pe']
            dy = r['div_yield']
            if pe:
                lines.append(f'  📈 PE={pe:.1f}' + (f' | Div={dy*100:.2f}%' if dy else ''))
            # strategy notes
            strat = r.get('strategy', {})
            if strat.get('notes'):
                lines.append(f'  📝 {strat["notes"]}')
            lines.append('')

    # Top 10
    top_syms = list(TOP10_STRATEGIES.keys())
    top_results = [r for r in results if r and r['symbol'] in top_syms]
    if top_results:
        lines.append('📋 *Top 10 候選策略*')
        lines.append('')
        for r in top_results:
            sig = r['entry_signal'] or 'N/A'
            sig_emoji = {'STRONG_BUY': '🟢🟢', 'BUY': '🟢', 'HOLD': '🟡', 'OVERBOUGHT': '🔴'}.get(sig, '⚪')
            lines.append(f'{sig_emoji} *{r["symbol"]}* — {r["name"]}')
            lines.append(f'  💰 ${r["price"]:.2f} | RSI(14)={r["rsi_14"]:.1f} | BIAS20={r["bias20"]:+.1f}%')
            lines.append(f'  🎯 {r["entry_signal"]} — {r["entry_zone"]}')
            strat = r.get('strategy', {})
            if strat.get('notes'):
                lines.append(f'  📝 {strat["notes"]}')
            if r['stop_loss'] and r['profit_target']:
                lines.append(f'  🛡 SL: ${r["stop_loss"]:.2f} | TP: ${r["profit_target"]:.2f}')
            lines.append('')

    # Summary
    buy_count = len([r for r in results if r and r['entry_signal'] in ('BUY', 'STRONG_BUY')])
    lines.append(f'🟢 {buy_count} BUY/STRONG_BUY signals')
    return '\n'.join(lines)

# ── Telegram push ──────────────────────────────────────────────────────────────
def push_telegram(message, chat_id='1616824689'):
    try:
        import requests
        env_path = os.path.join(BASE_DIR, '.env')
        bot_token = None
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        bot_token = line.split('=', 1)[1].strip()
                        break
        if not bot_token:
            print('  [WARN] TELEGRAM_BOT_TOKEN not found')
            return False
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        resp = requests.post(url, json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=15)
        if resp.status_code == 200:
            print('  [OK] Telegram sent')
            return True
        else:
            print(f'  [ERR] Telegram: {resp.status_code}')
            return False
    except Exception as e:
        print(f'  [ERR] Telegram push: {e}')
        return False

# ── Run ──────────────────────────────────────────────────────────────────────
def run(push=True):
    print('='*60)
    print('US Strategy Optimizer')
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)

    # Combine all symbols
    all_strategies = {**CORE_STRATEGIES, **TOP10_STRATEGIES}
    all_symbols = list(all_strategies.keys())

    print(f'\n[1] Analyzing {len(all_symbols)} stocks...')
    results = []
    for sym in all_symbols:
        strat = all_strategies[sym]
        r = analyze_stock(sym, strat)
        if r:
            r['strategy'] = strat
            results.append(r)
            sig = r['entry_signal'] or 'N/A'
            print(f'  {sym}: ${r["price"]:.2f} RSI={r["rsi_14"]:.1f} signal={sig}')

    print(f'\n[2] Saving config files...')
    # Save alert config
    alert_config = build_alert_config()
    with open(CONFIG_JSON, 'w', encoding='utf-8') as f:
        json.dump(alert_config, f, indent=2, ensure_ascii=False)
    print(f'  Saved: {CONFIG_JSON}')

    # Save strategy config
    strat_json = build_strategy_json()
    with open(STRATEGY_JSON, 'w', encoding='utf-8') as f:
        json.dump(strat_json, f, indent=2, ensure_ascii=False)
    print(f'  Saved: {STRATEGY_JSON}')

    print(f'\n[3] Building report...')
    report = build_report(results)
    print('\n' + report + '\n')

    if push:
        push_telegram(report)

    print('='*60)
    print('DONE')
    return results

if __name__ == '__main__':
    import sys
    dry = '--dry' in sys.argv
    run(push=not dry)
