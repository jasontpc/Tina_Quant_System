"""
Leo AI/半導體/科技 台股產業鏈 交易策略
Leo AI/Semi/Tech Taiwan Supply Chain Trading Strategy
專注：AI/半導體/科技 上中下游台股
"""

import sys, json, time, os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# Leo AI/科技/半導體 台股完整產業鏈
# ==========================================

# 上游 - 半導體/IC設計/關鍵材料
UPSTREAM = {
    '2330': {'name': '台積電', 'sector': '半導體', 'role': 'AI/HPC 晶片製造'},
    '2454': {'name': '聯發科', 'sector': 'IC設計', 'role': 'AI 手機/物聯網'},
    '2379': {'name': '瑞昱', 'sector': 'IC設計', 'role': '網通晶片/AIoT'},
    '3035': {'name': '智原', 'sector': 'IC設計', 'role': 'AI ASIC'},
    '3653': {'name': '健策', 'sector': '導線架', 'role': 'AI 功率元件'},
    '8016': {'name': '僑威', 'sector': '半導體耗材', 'role': 'AI 測試介面'},
    '3189': {'name': '景碩', 'sector': 'ABF載板', 'role': 'AI GPU 載板'},
}

# 中游 - 伺服器/板卡/封測/設備
MIDSTREAM = {
    '2382': {'name': '廣達', 'sector': '伺服器', 'role': 'AI 伺服器/GB200'},
    '3034': {'name': '緯穎', 'sector': '伺服器', 'role': 'AI 伺服器/雲端'},
    '4938': {'name': '和碩', 'sector': 'EMS', 'role': 'AI 硬體組裝'},
    '2376': {'name': '技嘉', 'sector': 'GPU板卡', 'role': 'AI GPU 伺服器'},
    '3665': {'name': '穎崴', 'sector': 'AI封測', 'role': 'AI CoWoS 封測'},
    '6153': {'name': '嘉澤', 'sector': '連接器', 'role': 'AI 高速連接'},
    '5269': {'name': '祥碩', 'sector': '高速傳輸', 'role': 'AI USB/PCIE'},
    '3515': {'name': '帆宣', 'sector': '半導體設備', 'role': 'AI 設備供應'},
    '6191': {'name': '志聖', 'sector': '設備', 'role': 'AI 熱處理設備'},
}

# 下游 - EMS/PCB/散熱/品牌
DOWNSTREAM = {
    '2317': {'name': '鴻海', 'sector': 'EMS', 'role': 'AI 伺服器/GB200'},
    '6706': {'name': '健鼎', 'sector': 'PCB', 'role': 'AI PCB/伺服器板'},
    '6271': {'name': '敦南', 'sector': 'PCB', 'role': 'AI 功率 PCB'},
    '3016': {'name': '奇鋐', 'sector': '散熱', 'role': 'AI 液冷/散熱'},
    '6230': {'name': '尼得科', 'sector': '散熱', 'role': 'AI 散熱風扇'},
    '4566': {'name': '研華', 'sector': '工業電腦', 'role': 'AI Edge IPC'},
}

# 合併所有股票
ALL_STOCKS = {}
ALL_STOCKS.update(UPSTREAM)
ALL_STOCKS.update(MIDSTREAM)
ALL_STOCKS.update(DOWNSTREAM)

# 去重
ALL_STOCKS = {k: v for k, v in ALL_STOCKS.items()}

# ==========================================
# 最佳交易參數（來自回測）
# ==========================================
BEST_PARAMS = {
    'rsi_entry_min': 30,
    'rsi_entry_max': 40,
    'hold_days_min': 5,
    'hold_days_max': 10,
    'tp_pct': 5,
    'sl_pct': 8,
    'win_rate': 85.7,
    'avg_return': 3.14,
}

# 警示閾值
ALERT_THRESHOLDS = {
    'overbought_rsi': 80,
    'watch_rsi': 70,
    'buy_rsi_max': 60,
    'margin_high': 0.25,
}

# ==========================================
# 交易信號評估
# ==========================================
def evaluate_signal(rsi, price_chg, sector):
    """評估進場信號"""
    signal = {
        'action': 'HOLD',      # BUY / WATCH / HOLD / SELL
        'confidence': 0,        # 1-5
        'reason': '',
        'rsi_entry': False,
        'tp_price': 0,
        'sl_price': 0,
    }
    
    # 進場條件：RSI 30-40
    if BEST_PARAMS['rsi_entry_min'] <= rsi <= BEST_PARAMS['rsi_entry_max']:
        signal['action'] = 'BUY'
        signal['rsi_entry'] = True
        signal['confidence'] = 5
        signal['reason'] = f'RSI {rsi:.1f} 符合進場區間'
    
    # 觀察條件：RSI 40-55
    elif 40 < rsi <= 55:
        signal['action'] = 'WATCH'
        signal['confidence'] = 3
        signal['reason'] = f'RSI {rsi:.1f} 接近超賣，等待回調'
    
    # 持有條件：RSI 55-70
    elif 55 < rsi <= 70:
        signal['action'] = 'HOLD'
        signal['confidence'] = 2
        signal['reason'] = f'RSI {rsi:.1f} 中性偏多，持有觀望'
    
    # 警戒條件：RSI 70-80
    elif 70 < rsi <= 80:
        signal['action'] = 'WATCH_SELL'
        signal['confidence'] = 1
        signal['reason'] = f'RSI {rsi:.1f} 過熱，考慮獲利了結'
    
    # 過熱條件：RSI > 80
    elif rsi > 80:
        signal['action'] = 'SELL'
        signal['confidence'] = 1
        signal['reason'] = f'RSI {rsi:.1f} 極度過熱，勿追價'
    
    return signal

# ==========================================
# 主程式
# ==========================================
def main():
    print('='*60)
    print('  Leo AI/半導體/科技 台股產業鏈 交易策略')
    print('  2026-04-29 收盤版')
    print('='*60)
    print()
    
    try:
        import yfinance as yf
        
        results = []
        strong = []; weak = []; neutral = []; buy_candidates = []
        
        today = time.strftime('%Y-%m-%d')
        
        # 處理所有股票
        for sym, info in ALL_STOCKS.items():
            try:
                ticker = yf.Ticker(f'{sym}.TW')
                h = ticker.history(period='30d', timeout=10)
                
                if h.empty or len(h) < 15:
                    continue
                
                closes = h['Close'].tolist()
                cur = closes[-1]
                prev = closes[-2] if len(closes) >= 2 else cur
                chg = (cur - prev) / prev * 100
                
                # RSI 計算
                import pandas as pd
                deltas = pd.Series(closes).diff()
                gain = deltas.clip(lower=0).rolling(14).mean()
                loss = (-deltas.clip(upper=0)).rolling(14).mean()
                rs = gain / loss
                rsi = float((100 - (100 / (1 + rs))).iloc[-1])
                
                # MA 計算
                ma20 = sum(closes[-20:]) / min(20, len(closes))
                ma60 = sum(closes[-60:]) / min(60, len(closes)) if len(closes) >= 60 else cur
                
                # 評估信號
                signal = evaluate_signal(rsi, chg, info['sector'])
                
                entry = {
                    'symbol': sym,
                    'name': info['name'],
                    'sector': info['sector'],
                    'role': info['role'],
                    'price': round(cur, 2),
                    'chg': round(chg, 2),
                    'rsi': round(rsi, 1),
                    'ma20': round(ma20, 2),
                    'ma60': round(ma60, 2),
                    'position': 'above_ma20' if cur > ma20 else 'below_ma20',
                    'action': signal['action'],
                    'confidence': signal['confidence'],
                    'reason': signal['reason'],
                }
                
                results.append(entry)
                
                # 分類
                if signal['action'] == 'BUY':
                    buy_candidates.append(entry)
                    strong.append(entry)
                elif chg > 3:
                    strong.append(entry)
                elif chg < -3:
                    weak.append(entry)
                else:
                    neutral.append(entry)
                    
            except Exception as e:
                pass
        
        # 排序：強勢 > 買入候選 > 中性 > 弱勢
        sorted_results = sorted(results, key=lambda x: (
            x['action'] == 'BUY',  # BUY first
            x['chg'],              # then by change
            x['rsi']               # then by RSI
        ), reverse=True)
        
        # 輸出
        print('【上游 - 半導體/IC設計/材料】')
        print('-'*60)
        for r in sorted_results:
            if '半導體' in r['sector'] or 'IC設計' in r['sector'] or 'RF' in r['sector'] or '導線' in r['sector'] or 'ABF' in r['sector'] or '耗材' in r['sector']:
                emoji = '🟢' if r['action'] == 'BUY' else '📗' if r['action'] == 'WATCH' else '➡️' if r['action'] == 'HOLD' else '🔴' if r['action'] == 'SELL' else '⚠️'
                print(f"  {emoji} {r['symbol']} {r['name']}")
                print(f"     {r['price']}  {r['chg']:+.1f}%  RSI:{r['rsi']}  MA20:{r['ma20']:.0f}")
                print(f"     [{r['role']}] {r['reason']}")
        
        print()
        print('【中游 - 伺服器/封測/設備】')
        print('-'*60)
        for r in sorted_results:
            if '伺服器' in r['sector'] or 'EMS' in r['sector'] or 'GPU' in r['sector'] or '封測' in r['sector'] or '連接' in r['sector'] or '設計服務' in r['sector'] or '傳輸' in r['sector'] or '設備' in r['sector']:
                emoji = '🟢' if r['action'] == 'BUY' else '📗' if r['action'] == 'WATCH' else '➡️' if r['action'] == 'HOLD' else '🔴' if r['action'] == 'SELL' else '⚠️'
                print(f"  {emoji} {r['symbol']} {r['name']}")
                print(f"     {r['price']}  {r['chg']:+.1f}%  RSI:{r['rsi']}  MA20:{r['ma20']:.0f}")
                print(f"     [{r['role']}] {r['reason']}")
        
        print()
        print('【下游 - EMS/PCB/散熱/品牌】')
        print('-'*60)
        for r in sorted_results:
            if 'EMS' in r['sector'] or '組裝' in r['sector'] or 'PCB' in r['sector'] or '散熱' in r['sector'] or '工業' in r['sector'] or 'AIoT' in r['sector'] or 'Edge' in r['sector']:
                emoji = '🟢' if r['action'] == 'BUY' else '📗' if r['action'] == 'WATCH' else '➡️' if r['action'] == 'HOLD' else '🔴' if r['action'] == 'SELL' else '⚠️'
                print(f"  {emoji} {r['symbol']} {r['name']}")
                print(f"     {r['price']}  {r['chg']:+.1f}%  RSI:{r['rsi']}  MA20:{r['ma20']:.0f}")
                print(f"     [{r['role']}] {r['reason']}")
        
        print()
        print('='*60)
        print(f'  總計: {len(results)} 檔 | 強勢: {len(strong)} | 中性: {len(neutral)} | 弱勢: {len(weak)}')
        print('='*60)
        
        # 買入候選
        print()
        print('【Leo 買入信號候選】(RSI 30-40)')
        print('-'*60)
        if buy_candidates:
            for r in buy_candidates[:5]:
                print(f"  🟢 {r['symbol']} {r['name']} ({r['sector']})")
                print(f"     股價: {r['price']}  RSI: {r['rsi']}  今日: {r['chg']:+.1f}%")
                tp = round(r['price'] * 1.05, 2)
                sl = round(r['price'] * 0.92, 2)
                print(f"     目標: {tp} (+5%)  停損: {sl} (-8%)")
        else:
            print('  無符合 RSI 30-40 的進場信號')
            print('  建議：等待市場回調至 RSI 30-40 再進場')
        
        # 過熱警示
        overbought = [r for r in results if r['rsi'] > 80]
        if overbought:
            print()
            print('【過熱警示 - 勿追價】')
            for r in overbought:
                print(f"  🔴 {r['symbol']} {r['name']} RSI={r['rsi']}")
        
        # 儲存
        out_dir = Path(__file__).parent
        out_file = out_dir / 'leo_ai_chain_strategy.json'
        
        strategy_data = {
            'date': today,
            'total_stocks': len(results),
            'strong': len(strong),
            'neutral': len(neutral),
            'weak': len(weak),
            'buy_candidates': buy_candidates,
            'overbought': overbought,
            'best_params': BEST_PARAMS,
            'all_stocks': results,
        }
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(strategy_data, f, ensure_ascii=False, indent=2)
        
        print()
        print(f'策略報告已儲存: {out_file}')
        print('完成!')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()