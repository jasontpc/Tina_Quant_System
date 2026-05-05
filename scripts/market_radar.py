# -*- coding: utf-8 -*-
"""
Tina Market Radar v1.0
=======================
市場雷達：主動狩獵系統
5階段：感測→篩選→建模→演練→提案

執行方式：python scripts/market_radar.py
Cron: 0 14 * * 1-5 (下午 market close 前主動出擊)
"""

import yfinance as yf
import requests
import sqlite3
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DB = WORKSPACE / "data" / "yfinance.db"
RADAR_LOG = WORKSPACE / "logs" / "market_radar.log"
CONFIG_DIR = WORKSPACE / "data" / "radar_candidates"

CONFIG_DIR.mkdir(exist_ok=True)

# ========== STAGE 1: 雷達感測 ==========

def scan_market_breadth():
    """廣度掃描：TWSE + 美股主要指數"""
    results = {}

    # TWSE 指數
    try:
        twii = yf.Ticker("^TWII").history(period="5d")
        if len(twii) >= 2:
            close = twii['Close']
            rsi14 = compute_rsi(close, 14)
            macd_v = compute_macd_hist(close)
            results['^TWII'] = {
                'price': float(close.iloc[-1]),
                'rsi': float(rsi14.iloc[-1]),
                'macd': float(macd_v.iloc[-1]),
                '5d_chg': float((close.iloc[-1]/close.iloc[-2]-1)*100)
            }
    except: pass

    # 美股主要指數
    for sym in ['^SPX', '^NDX', 'SPY', 'QQQ']:
        try:
            tk = yf.Ticker(sym)
            h = tk.history(period="5d")
            if len(h) >= 2:
                close = h['Close']
                results[sym] = {
                    'price': float(close.iloc[-1]),
                    'rsi': float(compute_rsi(close, 14).iloc[-1]),
                    'macd': float(compute_macd_hist(close).iloc[-1]),
                    '5d_chg': float((close.iloc[-1]/close.iloc[-2]-1)*100)
                }
        except: pass

    return results


def detect_volume_surge():
    """量能異常偵測：Local DB 內掃描"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    candidates = []
    # 抓近20日有足夠數據的股票
    c.execute("""
        SELECT symbol, date, close, volume
        FROM daily_ohlcv
        WHERE date >= date('now', '-30 days')
        AND symbol NOT LIKE '^%'
        ORDER BY symbol, date
    """)
    rows = c.fetchall()
    conn.close()

    # Group by symbol
    by_sym = defaultdict(list)
    for sym, dt, close, vol in rows:
        by_sym[sym].append({'date': dt, 'close': close, 'volume': vol})

    for sym, data in by_sym.items():
        if len(data) < 20:
            continue
        data = sorted(data, key=lambda x: x['date'])
        closes = [d['close'] for d in data]
        vols = [d['volume'] for d in data]

        avg_vol = sum(vols[-20:]) / 20
        last_vol = vols[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0

        # 量能突增 > 2x
        if vol_ratio > 2.0:
            price = closes[-1]
            rsi14 = compute_rsi(pd.Series(closes), 14).iloc[-1]
            macd_v = compute_macd_hist(pd.Series(closes)).iloc[-1]

            candidates.append({
                'symbol': sym,
                'price': price,
                'vol_ratio': round(vol_ratio, 2),
                'rsi': round(float(rsi14), 1),
                'macd': round(float(macd_v), 2),
                'reason': f'量能 {vol_ratio:.1f}x 爆量'
            })

    return candidates


def detect_limitup():
    """漲跌停偵測：TWSE 盤中"""
    try:
        r = requests.get(
            'https://www.twse.com.tw/rwd/zh/boostTick',
            params={'idx': 'ALL', 'time': '20260503'},
            timeout=10
        )
        data = r.json()
        items = data.get('data', []) or []

        limitup = []
        for item in items:
            try:
                name = item[0]
                code = item[1]
                chg_pct = float(item[7].replace('%', ''))
                if chg_pct >= 9.5:
                    limitup.append({
                        'code': code, 'name': name,
                        'chg_pct': chg_pct,
                        'reason': '漲停 +9.5%+'
                    })
                elif chg_pct <= -9.5:
                    limitup.append({
                        'code': code, 'name': name,
                        'chg_pct': chg_pct,
                        'reason': '跌停 -9.5%-'
                    })
            except: continue
        return limitup
    except:
        return []


# ========== STAGE 2: 大腦篩選 ==========

def brain_filter(candidates, breadth_data):
    """邏輯匹配審核"""
    filtered = []
    for c in candidates:
        score = 0
        reasons = []

        # RSI 進場區
        if c.get('rsi'):
            if 35 <= c['rsi'] <= 50:
                score += 30
                reasons.append(f'RSI {c["rsi"]:.0f} 進場區')
            elif c['rsi'] < 35:
                score += 15
                reasons.append(f'RSI {c["rsi"]:.0f} 超賣')

        # MACD 多頭
        if c.get('macd') and c['macd'] > 0:
            score += 25
            reasons.append('MACD 多頭')

        # 量能爆量
        if c.get('vol_ratio', 0) > 2.5:
            score += 20
            reasons.append(f'量能 {c["vol_ratio"]}x')

        # 板塊動能
        if 'TWII' in breadth_data:
            if breadth_data['^TWII']['rsi'] < 60:
                score += 10
                reasons.append('大盤 RSI 適中')

        c['score'] = score
        c['reasons'] = reasons
        c['priority'] = '高度關注' if score >= 60 else ('持續觀察' if score >= 30 else '暫時排除')

        if score >= 30:
            filtered.append(c)

    return sorted(filtered, key=lambda x: -x['score'])


# ========== STAGE 3: 虛擬建模 ==========

def generate_virtual_config(candidate):
    """自動配置生成"""
    sym = candidate['symbol']
    config = {
        'symbol': sym,
        'discovered_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'source': 'market_radar',
        'virtual': True,
        'entry_criteria': {
            'rsi_max': 50,
            'rsi_min': 30,
            'macd_positive': True,
            'ma_bullish': True
        },
        'risk_params': {
            'stop_loss_pct': 10,
            'take_profit_pct': 8
        },
        'score': candidate.get('score', 0),
        'reasons': candidate.get('reasons', []),
        'vol_ratio': candidate.get('vol_ratio', 0),
        'status': 'virtual_tracking'
    }
    return config


# ========== STAGE 4: 沙盒演練 ==========

def sandbox_backtest(symbol):
    """虛擬建倉測試"""
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period='1y')
        if len(h) < 60:
            return None

        closes = h['Close']
        rsi_series = compute_rsi(closes, 14)
        macd_series = compute_macd_hist(closes)
        sma20 = closes.ewm(span=20, adjust=False).mean()
        sma60 = closes.ewm(span=60, adjust=False).mean()

        trades = []
        for i in range(60, len(closes)):
            rsi_v = float(rsi_series.iloc[i])
            macd_v = float(macd_series.iloc[i])
            ma20 = float(sma20.iloc[i])
            ma60 = float(sma60.iloc[i])
            price = float(closes.iloc[i])

            # 進場：RSI 30-50 + MACD>0 + MA多头
            if 30 <= rsi_v <= 50 and macd_v > 0 and ma20 > ma60:
                entry_price = price
                for j in range(i+1, min(i+21, len(closes))):
                    exit_price = float(closes.iloc[j])
                    pnl = (exit_price - entry_price) / entry_price * 100
                    if pnl <= -8 or pnl >= 8:
                        trades.append({'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'days': j-i})
                        break

        if not trades:
            return None

        win_rate = sum(1 for t in trades if t['pnl'] > 0) / len(trades) * 100
        avg_pnl = sum(t['pnl'] for t in trades) / len(trades)

        return {
            'symbol': symbol,
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1),
            'avg_pnl': round(avg_pnl, 2),
            'trades': trades[-10:]  # 最近10筆
        }
    except Exception as e:
        return None


# ========== STAGE 5: 報告生成 ==========

def build_report(breadth, volume_surge, limitup, filtered, sandbox_results):
    lines = []
    lines.append("=" * 65)
    lines.append("  📡 Tina Market Radar 市場雷達報告")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 65)
    lines.append("")

    # Stage 1: 廣度掃描
    lines.append("[Stage 1] 🌐 市場廣度掃描")
    for sym, d in breadth.items():
        rsi_s = '🟢' if d['rsi'] < 40 else ('🔵' if d['rsi'] < 60 else '🔴')
        macd_s = '🟢' if d['macd'] > 0 else '🔴'
        lines.append(f"  {sym:8s} ${d['price']:,.0f}  RSI {d['rsi']:.0f}{rsi_s}  MACD {d['macd']:+.2f}{macd_s}  5d {d['5d_chg']:+.1f}%")
    lines.append("")

    # Stage 2: 量能異常
    lines.append(f"[Stage 2] 📊 量能異常偵測 ({len(volume_surge)} 檔)")
    for c in volume_surge[:10]:
        lines.append(f"  {c['symbol']:10s} ${c['price']:.2f}  RSI {c.get('rsi','?') or '?':.0f}  量能 {c['vol_ratio']}x  {c['reason']}")
    lines.append("")

    # Stage 3: 漲跌停
    if limitup:
        lines.append(f"[Stage 3] 🚨 漲跌停 ({len(limitup)} 檔)")
        for l in limitup[:10]:
            tag = '🔴' if l['chg_pct'] > 0 else '🔵'
            lines.append(f"  {tag} {l['code']} {l['name']} {l['chg_pct']:+.1f}%")
        lines.append("")

    # Stage 4: 優先級排序
    if filtered:
        lines.append(f"[Stage 4] 🎯 機會優先級排序")
        for c in filtered[:10]:
            priority_icon = '🟢' if c['priority'] == '高度關注' else ('🟡' if c['priority'] == '持續觀察' else '⚪')
            sb = sandbox_results.get(c['symbol'], {})
            sb_info = f" | 沙盒 WR {sb.get('win_rate','?')}% 平均 {sb.get('avg_pnl','?')}%+" if sb else ""
            lines.append(f"  {priority_icon} [{c['priority']}] {c['symbol']:10s} Score={c['score']}  RSI={c.get('rsi','?')}  MACD={c.get('macd','?')}{sb_info}")
            lines.append(f"           {' / '.join(c.get('reasons', []))}")
        lines.append("")

    # Stage 5: 行動建議
    lines.append("[Stage 5] 📋 行動建議")
    high = [c for c in filtered if c['priority'] == '高度關注']
    if high:
        lines.append(f"  🟢 高度關注 ({len(high)} 檔)：{', '.join(c['symbol'] for c in high)}")
        lines.append("     → 建議進入沙盒演練，模擬建倉測試")
    medium = [c for c in filtered if c['priority'] == '持續觀察']
    if medium:
        lines.append(f"  🟡 持續觀察 ({len(medium)} 檔)：{', '.join(c['symbol'] for c in medium[:5])}")

    lines.append("")
    lines.append("=" * 65)
    return "\n".join(lines)


# ========== 主程式 ==========

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss))


def compute_macd_hist(series, fast=12, slow=26, signal=9):
    ema12 = series.ewm(span=fast, adjust=False).mean()
    ema26 = series.ewm(span=slow, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=signal, adjust=False).mean()
    return macd_l - macd_s


def main():
    print("=" * 65)
    print("  📡 Tina Market Radar 系統啟動")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    # Stage 1: 廣度掃描
    print("[1/5] 🌐 廣度掃描...")
    breadth = scan_market_breadth()

    # Stage 2: 量能異常
    print("[2/5] 📊 量能異常偵測...")
    volume_surge = detect_volume_surge()

    # Stage 3: 漲跌停
    print("[3/5] 🚨 漲跌停偵測...")
    limitup = detect_limitup()

    # Stage 4: 大腦篩選
    print("[4/5] 🧠 大腦篩選...")
    filtered = brain_filter(volume_surge, breadth)

    # Stage 5: 沙盒演練
    print("[5/5] 🎮 沙盒演練...")
    sandbox_results = {}
    for c in filtered[:5]:
        result = sandbox_backtest(c['symbol'])
        if result:
            sandbox_results[c['symbol']] = result

    # 生成虛擬配置
    configs = []
    for c in filtered[:3]:
        cfg = generate_virtual_config(c)
        sym = c['symbol']
        cfg_path = CONFIG_DIR / f"{sym.replace('.','_')}.json"
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        configs.append(cfg)

    # 產出報告
    report = build_report(breadth, volume_surge, limitup, filtered, sandbox_results)
    print(report)

    # 寫入日誌
    RADAR_LOG.parent.mkdir(exist_ok=True)
    with open(RADAR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*65}\n")
        f.write(f"Market Radar Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Volume surge candidates: {len(volume_surge)}\n")
        f.write(f"High priority: {len([c for c in filtered if c['priority']=='高度關注'])}\n")
        f.write(f"Limitup: {len(limitup)}\n")
        f.write(f"Sandbox tested: {len(sandbox_results)}\n")
        f.write(f"Virtual configs created: {len(configs)}\n")

    print()
    print(f"✅ 雷達掃描完成")
    print(f"   量能異常候選: {len(volume_surge)} 檔")
    print(f"   高度關注: {len([c for c in filtered if c['priority']=='高度關注'])} 檔")
    print(f"   漲跌停: {len(limitup)} 檔")
    print(f"   沙盒測試: {len(sandbox_results)} 檔")
    print(f"   虛擬配置: {len(configs)} 檔")
    print("=" * 65)

    return report


if __name__ == '__main__':
    report = main()
    print("\n" + report)