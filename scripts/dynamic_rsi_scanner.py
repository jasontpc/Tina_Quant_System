# -*- coding: utf-8 -*-
"""
Tina Brain - Dynamic RSI Scanner v1.0
=====================================
根據TWII RSI動態調整進場門檻
"""
import yfinance as yf
import numpy as np
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

def calc_rsi(close, period=14):
    delta = close.diff().dropna()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs)))

def calc_atr(h, period=14):
    tr = np.maximum(h['High']-h['Low'], 
                    np.maximum(abs(h['High']-h['Close'].shift(1)), 
                               abs(h['Low']-h['Close'].shift(1))))
    return tr.rolling(period).mean()

def get_dynamici_threshold(twii_rsi, base_leo=50, base_nana=40):
    """根據TWII RSI動態調整門檻"""
    if twii_rsi > 85:  # 過熱
        return {'leo': 35, 'nana': 30, 'position_mult': 0.5}
    elif twii_rsi > 70:  # 多頭
        return {'leo': 40, 'nana': 35, 'position_mult': 1.0}
    elif twii_rsi > 50:  # 中性
        return {'leo': 45, 'nana': 40, 'position_mult': 1.5}
    elif twii_rsi > 30:  # 整理
        return {'leo': 50, 'nana': 45, 'position_mult': 2.0}
    else:  # 超賣
        return {'leo': 55, 'nana': 50, 'position_mult': 0}

def check_stock_entry(sym, name, threshold):
    t = yf.Ticker(sym)
    h = t.history(period="3mo")
    if len(h) < 60: return None
    
    price = float(h['Close'].iloc[-1])
    close_hist = h['Close']
    ma20 = close_hist.rolling(20).mean().iloc[-1]
    ma60 = close_hist.rolling(60).mean().iloc[-1]
    rsi = float(calc_rsi(close_hist).iloc[-1])
    atr = float(calc_atr(h).iloc[-1])
    atr_pct = atr / price * 100
    
    # MA篩選
    ma_ok = (ma20 > ma60) if not (np.isnan(ma20) or np.isnan(ma60)) else False
    
    # 進場評估
    if ma_ok and rsi < threshold['leo']:
        stop_loss = price - atr * 2.5
        target = price * 1.08
        risk = (price - stop_loss) / price * 100
        reward = (target - price) / price * 100
        rr = reward / risk if risk > 0 else 0
        
        return {
            'symbol': sym,
            'name': name,
            'price': price,
            'rsi': rsi,
            'ma_ok': ma_ok,
            'atr_pct': atr_pct,
            'stop_loss': stop_loss,
            'target': target,
            'risk_pct': risk,
            'reward_pct': reward,
            'rr': rr,
            'position_mult': threshold['position_mult']
        }
    return None

def run_scan():
    print("="*70)
    print("  Tina Dynamic RSI Scanner v1.0")
    print("="*70)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # TWII RSI
    twii = yf.Ticker("^TWII")
    h = twii.history(period="3mo")
    twii_rsi = float(calc_rsi(h['Close']).iloc[-1])
    twii_price = float(h['Close'].iloc[-1])
    
    print(f"\n大盤：TWII {twii_price:.0f} RSI={twii_rsi:.1f}")
    
    threshold = get_dynamici_threshold(twii_rsi)
    print(f"動態門檻：Leo RSI<{threshold['leo']} / Nana RSI<{threshold['nana']} / 倉位{threshold['position_mult']}x")
    print()
    
    # 掃描 Leo
    leo_stocks = [
        ('3037.TW','欣興'),('3189.TW','景碩'),('2360.TW','致茂'),
        ('3665.TW','穎崴'),('2345.TW','智邦'),('2383.TW','台光電'),
        ('2449.TW','京元電'),('3017.TW','奇力新'),('2308.TW','台達電'),
        ('3016.TW','嘉晶'),('2330.TW','台積電'),
    ]
    
    # 掃描 Nana
    nana_stocks = [
        ('2454.TW','聯發科'),('6442.TW','光聖'),('2359.TW','所羅門'),
        ('3231.TW','緯創'),('2317.TW','鴻海'),('2382.TW','廣達'),
        ('6239.TW','力成'),
    ]
    
    all_signals = []
    
    print("Leo 波段掃描:")
    for sym, name in leo_stocks:
        result = check_stock_entry(sym, name, threshold)
        if result:
            result['team'] = 'Leo'
            all_signals.append(result)
            print(f"  ✅ {name}: ${result['price']:.0f} RSI={result['rsi']:.1f} ATR={result['atr_pct']:.1f}%")
            print(f"     停損${result['stop_loss']:.0f} 目標${result['target']:.0f} RR={result['rr']:.2f}")
        else:
            try:
                t = yf.Ticker(sym)
                h = t.history(period="3mo")
                if len(h) >= 60:
                    rsi = float(calc_rsi(h['Close']).iloc[-1])
                    print(f"  ⏸️ {name}: RSI={rsi:.1f} (未達門檻{threshold['leo']})")
            except: pass
    
    print("\nNana 波段掃描:")
    for sym, name in nana_stocks:
        result = check_stock_entry(sym, name, threshold)
        if result:
            result['team'] = 'Nana'
            all_signals.append(result)
            print(f"  ✅ {name}: ${result['price']:.0f} RSI={result['rsi']:.1f} ATR={result['atr_pct']:.1f}%")
            print(f"     停損${result['stop_loss']:.0f} 目標${result['target']:.0f} RR={result['rr']:.2f}")
        else:
            try:
                t = yf.Ticker(sym)
                h = t.history(period="3mo")
                if len(h) >= 60:
                    rsi = float(calc_rsi(h['Close']).iloc[-1])
                    print(f"  ⏸️ {name}: RSI={rsi:.1f} (未達門檻{threshold['nana']})")
            except: pass
    
    # 排序
    print("\n" + "="*70)
    print("  信號排名（按RR排序）")
    print("="*70)
    
    if all_signals:
        all_signals.sort(key=lambda x: x['rr'], reverse=True)
        for i, s in enumerate(all_signals, 1):
            pos_size = 5 * s['position_mult']
            print(f"{i}. {s['name']} [{s['team']}] RSI={s['rsi']:.1f} RR={s['rr']:.2f} 建議倉位{pos_size:.1f}%")
    else:
        print("  無進場信號")
    
    # Save
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'twii_rsi': twii_rsi,
        'threshold': threshold,
        'signals': all_signals
    }
    
    with open(DATA / 'dynamic_rsi_signals.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已存至 dynamic_rsi_signals.json")
    return all_signals

if __name__ == "__main__":
    run_scan()