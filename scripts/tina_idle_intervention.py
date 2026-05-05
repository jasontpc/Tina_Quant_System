"""
Tina 閒置主動介入系統
當系統閒置時，大腦主動執行有意義的任務
"""

import os
import sys
import json
import yfinance as yf
from datetime import datetime, timedelta

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
STRATEGIES_DIR = os.path.join(WORKSPACE, 'configs', 'stock_strategies')
DATA_DIR = os.path.join(WORKSPACE, 'data')
REPORTS_DIR = os.path.join(WORKSPACE, 'reports')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ============================================================================
# 任務1：市場掃描 - 尋找新機會
# ============================================================================

def task_market_scan():
    log("\n[TASK 1] 市場掃描 - 尋找新機會")
    log("-"*40)
    
    # TW 候選股票池（不在36檔中的潛力股）
    tw_pool = [
        ('2303 聯電', '2303.TW'),
        ('2308 台達電', '2308.TW'),
        ('2412 中華電', '2412.TW'),
        ('2882 國泰金', '2882.TW'),
        ('2892 第一金', '2892.TW'),
        ('2610 華航', '2610.TW'),
        ('2618 長榮航', '2618.TW'),
        ('3044 聯強', '3044.TW'),
    ]
    
    candidates = []
    
    for name, ticker in tw_pool:
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period='3mo')
            if len(h) < 30:
                continue
            
            price = float(h['Close'].iloc[-1])
            rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
            info = tk.info
            rev_g = info.get('revenueGrowth', 0) or 0
            pe = info.get('trailingPE', 0) or 0
            
            # 評分
            score = 0
            if 35 <= rsi <= 65:
                score += 3
            elif rsi < 35:
                score += 2
            if rev_g > 0.2:
                score += 2
            if pe > 0 and pe < 20:
                score += 2
            
            if score >= 5:
                candidates.append({
                    'name': name,
                    'ticker': ticker,
                    'price': price,
                    'rsi': rsi,
                    'rev_g': rev_g,
                    'pe': pe,
                    'score': score
                })
        except:
            pass
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    log(f"發現 {len(candidates)} 檔潛力股")
    for c in candidates[:5]:
        pe_s = str(round(c['pe'])) if c['pe'] > 0 else 'N/A'
        log(f"  {c['name']}: ${c['price']:.2f} RSI={c['rsi']:.1f} Rev={c['rev_g']*100:.0f}% PE={pe_s} Score={c['score']}")
    
    return candidates

# ============================================================================
# 任務2：相關性檢查 - 風險分散
# ============================================================================

def task_correlation_check():
    log("\n[TASK 2] 相關性檢查 - 風險分散分析")
    log("-"*40)
    
    # 主要持股
    stocks = ['2330.TW', '2382.TW', '2881.TW', '2883.TW', '3231.TW']
    names = ['台積電', '廣達', '富邦金', '凱基金', '緯創']
    
    prices = {}
    for ticker, name in zip(stocks, names):
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period='3mo')
            if len(h) >= 60:
                prices[name] = h['Close']
        except:
            pass
    
    if len(prices) < 2:
        log("數據不足，跳過相關性檢查")
        return
    
    # 計算相關性矩陣（簡化版）
    import numpy as np
    
    assets = list(prices.keys())
    n = len(assets)
    
    log(f"分析 {n} 檔股票的相關性...")
    
    # 簡單計算：同時創新高/新低的次數
    correlations = []
    for i in range(n):
        for j in range(i+1, n):
            a = assets[i]
            b = assets[j]
            
            # 計算rolling回報
            ret_a = prices[a].pct_change().dropna()
            ret_b = prices[b].pct_change().dropna()
            
            # 找到共同期間
            min_len = min(len(ret_a), len(ret_b))
            if min_len < 20:
                continue
            
            ret_a = ret_a.iloc[-min_len:]
            ret_b = ret_b.iloc[-min_len:]
            
            # 相關係數
            corr = ret_a.corr(ret_b)
            
            correlations.append({
                'stock_a': a,
                'stock_b': b,
                'corr': corr
            })
            
            corr_level = '高' if abs(corr) > 0.6 else '中' if abs(corr) > 0.3 else '低'
            log(f"  {a} vs {b}: {corr:.2f} ({corr_level}相關)")
    
    # 找出高相關對（風險集中）
    high_corr = [c for c in correlations if c['corr'] > 0.6]
    if high_corr:
        log(f"\n⚠️ 警告：發現 {len(high_corr)} 組高相關股票對")
        log("  建議：適當分散部位，避免風險集中")
    
    return correlations

# ============================================================================
# 任務3：市場情緒報告
# ============================================================================

def task_market_sentiment():
    log("\n[TASK 3] 市場情緒報告")
    log("-"*40)
    
    # 主要指數
    indices = [
        ('^TWII', '加權指數'),
        ('^GSPC', 'S&P 500'),
        ('^IXIC', 'NASDAQ'),
        ('^SOX', '費半')
    ]
    
    sentiments = []
    
    for ticker, name in indices:
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period='1mo')
            if len(h) < 20:
                continue
            
            price = float(h['Close'].iloc[-1])
            rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
            ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
            ma60 = float(h['Close'].rolling(60).mean().iloc[-1]) if len(h) >= 60 else ma20
            
            above_ma20 = price > ma20
            above_ma60 = price > ma60
            
            if rsi > 75:
                sentiment = '🔥 過熱'
            elif rsi > 60:
                sentiment = '📈 多頭'
            elif rsi < 40:
                sentiment = '📉 超賣'
            else:
                sentiment = '➡️ 中性'
            
            status = '✅' if above_ma20 and above_ma60 else '⚠️' if above_ma20 else '❌'
            
            log(f"{status} {name}: {price:.2f} RSI={rsi:.1f} {sentiment}")
            
            sentiments.append({
                'name': name,
                'price': price,
                'rsi': rsi,
                'sentiment': sentiment,
                'above_ma20': above_ma20,
                'above_ma60': above_ma60
            })
        except:
            pass
    
    return sentiments

# ============================================================================
# 任務4：策略健康度報告
# ============================================================================

def task_strategy_health():
    log("\n[TASK 4] 策略健康度報告")
    log("-"*40)
    
    cooldown_file = os.path.join(DATA_DIR, 'active_brain_v2_cooldown.json')
    
    if os.path.exists(cooldown_file):
        with open(cooldown_file, 'r') as f:
            cooldown = json.load(f)
        
        log(f"目前有 {len(cooldown)} 檔股票在冷卻期")
        for code, info in cooldown.items():
            last = datetime.fromisoformat(info['time'])
            remaining = 86400 - (datetime.now() - last).total_seconds()
            if remaining > 0:
                hours = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                log(f"  {code}: 還有 {hours}h {mins}min 恢復")
    else:
        log("無冷卻記錄")
    
    # 策略檔案數量
    if os.path.exists(STRATEGIES_DIR):
        count = len([f for f in os.listdir(STRATEGIES_DIR) if f.endswith('.json')])
        log(f"已配置策略: {count} 檔")
    
    return True

# ============================================================================
# 任務5：市場机会扫描
# ============================================================================

def task_opportunity_scan():
    log("\n[TASK 5] 市場機會掃描")
    log("-"*40)
    
    # 低價價值股（TW + US）
    opportunities = []
    
    # TW 低價股
    tw_candidates = [
        ('2883 凱基金', '2883.TW', 21.50),
        ('2884 玉山金', '2884.TW', 31.85),
        ('2891 中信金', '2891.TW', 52.30),
    ]
    
    for name, ticker, baseline in tw_candidates:
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period='1mo')
            price = float(h['Close'].iloc[-1])
            rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
            
            if rsi < 55:
                opportunities.append({
                    'name': name,
                    'market': 'TW',
                    'price': price,
                    'rsi': rsi,
                    'reason': 'RSI理想'
                })
        except:
            pass
    
    # US 低價股
    us_candidates = [
        ('DLO Deloitte', 'DLO', 13.75),
        ('GEN Gen', 'GEN', 19.37),
        ('RIVN Rivian', 'RIVN', 15.02),
    ]
    
    for name, ticker, baseline in us_candidates:
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period='1mo')
            price = float(h['Close'].iloc[-1])
            rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
            
            if rsi < 60:
                opportunities.append({
                    'name': name,
                    'market': 'US',
                    'price': price,
                    'rsi': rsi,
                    'reason': '動能持續'
                })
        except:
            pass
    
    opportunities.sort(key=lambda x: x['rsi'])
    
    log(f"發現 {len(opportunities)} 檔機會股")
    for o in opportunities[:6]:
        log(f"  [{o['market']}] {o['name']}: ${o['price']:.2f} RSI={o['rsi']:.1f} ({o['reason']})")
    
    return opportunities

# ============================================================================
# 主流程
# ============================================================================

def main():
    now = datetime.now()
    
    log("="*60)
    log("TINA 閒置主動介入系統")
    log("="*60)
    log(f"啟動時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"系統狀態: 閒置中，主動介入")
    
    # 執行5個任務
    results = {}
    
    results['market_scan'] = task_market_scan()
    results['correlation'] = task_correlation_check()
    results['sentiment'] = task_market_sentiment()
    results['strategy_health'] = task_strategy_health()
    results['opportunities'] = task_opportunity_scan()
    
    # 總結
    log("\n" + "="*60)
    log("主動介入完成 - 任務總結")
    log("="*60)
    
    market_opp = len(results.get('market_scan', []))
    sentiments = results.get('sentiment', [])
    opportunities = results.get('opportunities', [])
    
    log(f"  發現 {market_opp} 檔潛力股")
    log(f"  分析 {len(sentiments)} 個市場情緒")
    log(f"  找到 {len(opportunities)} 檔機會股")
    
    log("\n[TINA 大腦建議]")
    
    # 生成建議
    if opportunities:
        top = opportunities[0]
        log(f"  最佳進場: {top['name']} (RSI {top['rsi']:.1f})")
    
    if sentiments:
        hot = [s for s in sentiments if '過熱' in s['sentiment']]
        oversold = [s for s in sentiments if '超賣' in s['sentiment']]
        
        if hot:
            log(f"  市場過熱: {', '.join([s['name'] for s in hot])}")
        if oversold:
            log(f"  超賣關注: {', '.join([s['name'] for s in oversold])}")
    
    log("\n[TINA 大腦已主動介入優化系統]")

if __name__ == '__main__':
    main()