# -*- coding: utf-8 -*-
"""
Leo 法人+RSI 雙重篩選系統
結合技術面（RSI）與基本面（法人籌碼）進行選股

篩選邏輯：
  ① RSI < 50（技術面超賣）
  ② 投信連續買超 > 3天（法人背書）
  ③ 近月營收年增 > 0%（基本面支撐）
  ④ 20日動量 > -5%（動能保護）

使用方式：
  python leo_dual_filter.py              # 全市場掃描
  python leo_dual_filter.py 2330         # 單一股票分析
  python leo_dual_filter.py --batch      # 批次分析Leo名單
  python leo_dual_filter.py --export     # 匯出結果
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time
from datetime import datetime, timedelta
import numpy as np
import requests

# yfinance
import yfinance as yf

# FinMind Token
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'

# Leo 追蹤名單
LEO_STOCKS = {
    '2330': {'name': '台積電', 'rsi_th': 50},
    '2382': {'name': '廣達', 'rsi_th': 50},
    '3665': {'name': '穎崴', 'rsi_th': 50},
    '2317': {'name': '鴻海', 'rsi_th': 55},
    '3034': {'name': '緯穎', 'rsi_th': 40},
}

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\data'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def calc_rsi(prices, period=14):
    """計算 RSI"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    return float(100 - (100 / (1 + avg_gain / avg_loss)))


def get_rsi_and_momentum(code):
    """取得 RSI 和 動量"""
    try:
        tk = yf.download(f'{code}.TW', period='3mo', progress=False)
        if tk.empty:
            return None, None, None, None
        
        close = tk['Close'].squeeze().values
        price = float(close[-1])
        prev = float(close[-2]) if len(close) > 1 else price
        change = (price / prev - 1) * 100
        
        rsi = calc_rsi(close, 14)
        
        # 20日動量
        mom20 = float((close[-1] / close[-21] - 1) * 100) if len(close) >= 21 else 0
        
        # MA20, MA60
        ma20 = float(np.mean(close[-20:])) if len(close) >= 20 else None
        ma60 = float(np.mean(close[-60:])) if len(close) >= 60 else None
        
        return price, change, rsi, mom20, ma20, ma60
    except Exception as e:
        return None, None, None, None, None, None


def get_inst_buy_days(code, days=5):
    """取得投信連續買超天數"""
    url = 'https://api.finmindtrade.com/api/v4/data'
    headers = {'Authorization': f'Bearer {FINMIND_TOKEN}'}
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days+5)).strftime('%Y-%m-%d')
    
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': code,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return 0, 0
        
        data = resp.json().get('data', [])
        
        # 計算投信每日淨買超
        daily_net = {}
        for row in data:
            date = row.get('date', '')[:10]
            name = row.get('name', '')
            if name != 'Investment_Trust':
                continue
            
            buy = row.get('buy', 0) or 0
            sell = row.get('sell', 0) or 0
            net = buy - sell
            daily_net[date] = net
        
        # 計算連續買超天數
        sorted_dates = sorted(daily_net.keys(), reverse=True)
        consecutive_buy_days = 0
        total_net = 0
        
        for date in sorted_dates[:days]:
            net = daily_net.get(date, 0)
            if net > 0:
                consecutive_buy_days += 1
                total_net += net
            else:
                break
        
        return consecutive_buy_days, total_net
        
    except Exception as e:
        print(f"  [INST ERROR] {e}")
        return 0, 0


def get_revenue_yoy(code):
    """取得月營收年增率"""
    url = 'https://api.finmindtrade.com/api/v4/data'
    headers = {'Authorization': f'Bearer {FINMIND_TOKEN}'}
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    params = {
        'dataset': 'TaiwanStockMonthRevenue',
        'data_id': code,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return None
        
        data = resp.json().get('data', [])
        if not data:
            return None
        
        # 取最新一筆有 YoY 的資料
        for row in sorted(data, key=lambda x: x.get('date', ''), reverse=True):
            yoy = row.get('yoy')
            if yoy is not None:
                return float(yoy)
        
        return None
        
    except Exception as e:
        return None


def analyze_stock(code):
    """分析單一股票"""
    print(f"\n{'='*60}")
    print(f"【{code}】{LEO_STOCKS.get(code, {}).get('name', 'N/A')}")
    print(f"{'='*60}")
    
    # 技術面
    price, change, rsi, mom20, ma20, ma60 = get_rsi_and_momentum(code)
    
    if price is None:
        print("  ❌ 無法取得股價資料")
        return None
    
    print(f"\n📊 技術面：")
    print(f"  現價: {price:,.0f} ({change:+.2f}%)")
    print(f"  RSI: {rsi:.1f}")
    print(f"  20日動量: {mom20:+.2f}%")
    print(f"  MA20: {ma20:,.0f}" if ma20 else "  MA20: N/A")
    print(f"  MA60: {ma60:,.0f}" if ma60 else "  MA60: N/A")
    
    # 法人面
    print(f"\n🏦 法人面：")
    buy_days, total_net = get_inst_buy_days(code, days=5)
    print(f"  投信連續買超: {buy_days} 天")
    print(f"  投信淨買超: {total_net:+,.0f} 股")
    
    # 基本面
    print(f"\n📈 基本面：")
    yoy = get_revenue_yoy(code)
    print(f"  月營收年增率: {yoy:+.1f}%" if yoy is not None else "  月營收年增率: N/A")
    
    # 評分
    print(f"\n🎯 篩選評分：")
    
    tech_score = 0
    inst_score = 0
    fund_score = 0
    
    # 技術面評分（40分）
    rsi_th = LEO_STOCKS.get(code, {}).get('rsi_th', 50)
    if rsi < rsi_th - 10:
        tech_score += 20
        print(f"  ✅ RSI {rsi:.1f} < {rsi_th - 10}（超賣） [+20]")
    elif rsi < rsi_th:
        tech_score += 10
        print(f"  🟡 RSI {rsi:.1f} < {rsi_th}（偏低） [+10]")
    else:
        print(f"  ❌ RSI {rsi:.1f} >= {rsi_th}（偏高） [+0]")
    
    if mom20 > -5:
        tech_score += 20
        print(f"  ✅ 動量 {mom20:+.2f}% > -5% [+20]")
    else:
        print(f"  ❌ 動量 {mom20:+.2f}% <= -5% [+0]")
    
    # 法人面評分（30分）
    if buy_days >= 3:
        inst_score += 30
        print(f"  ✅ 投信連續買超 {buy_days} 天 [+30]")
    elif buy_days >= 1:
        inst_score += 15
        print(f"  🟡 投信買超 {buy_days} 天 [+15]")
    else:
        print(f"  ❌ 投信無連續買超 [+0]")
    
    # 基本面評分（30分）
    if yoy is not None and yoy > 0:
        fund_score += 30
        print(f"  ✅ 營收年增 {yoy:+.1f}% > 0% [+30]")
    elif yoy is not None:
        fund_score += 10
        print(f"  🟡 營收年增 {yoy:+.1f}% [+10]")
    else:
        print(f"  ⚠️ 營收資料無法取得 [+0]")
    
    total = tech_score + inst_score + fund_score
    
    print(f"\n{'='*60}")
    print(f"📊 總分: {total}/100")
    print(f"   技術面: {tech_score}/40")
    print(f"   法人面: {inst_score}/30")
    print(f"   基本面: {fund_score}/30")
    
    # 進場建議
    print(f"\n{'='*60}")
    if total >= 80:
        print(f"  ✅✅ 強烈進場（{total}分）")
        action = 'STRONG_BUY'
    elif total >= 60:
        print(f"  ✅ 可進場（{total}分）")
        action = 'BUY'
    elif total >= 40:
        print(f"  🟡 觀望（{total}分）")
        action = 'HOLD'
    else:
        print(f"  ❌ 觀望（{total}分）")
        action = 'WAIT'
    
    result = {
        'code': code,
        'name': LEO_STOCKS.get(code, {}).get('name', 'N/A'),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'price': price,
        'change_pct': change,
        'rsi': round(rsi, 1),
        'mom20': round(mom20, 2),
        'ma20': ma20,
        'ma60': ma60,
        'inst_buy_days': buy_days,
        'inst_net': total_net,
        'revenue_yoy': yoy,
        'tech_score': tech_score,
        'inst_score': inst_score,
        'fund_score': fund_score,
        'total_score': total,
        'action': action,
    }
    
    print(f"{'='*60}")
    
    return result


def scan_all():
    """掃描所有 Leo 股票"""
    print("\n🔍 全市場掃描中...")
    results = []
    
    for code in LEO_STOCKS.keys():
        result = analyze_stock(code)
        if result:
            results.append(result)
        time.sleep(1)  # 避免 API 請求過快
    
    # 排序
    results = sorted(results, key=lambda x: x['total_score'], reverse=True)
    
    # 顯示摘要
    print("\n\n" + "="*70)
    print("📊 Leo 法人+RSI 雙重篩選結果摘要")
    print("="*70)
    print(f"{'代號':<6} {'名稱':<8} {'現價':>8} {'RSI':>6} {'投信天':>6} {'營收Yoy':>8} {'總分':>5} {'建議':<12}")
    print("-"*70)
    
    for r in results:
        yoy_str = f"{r['revenue_yoy']:+.1f}%" if r['revenue_yoy'] else "N/A"
        print(f"{r['code']:<6} {r['name']:<8} {r['price']:>8,.0f} {r['rsi']:>6.1f} {r['inst_buy_days']:>6} {yoy_str:>8} {r['total_score']:>5} {r['action']:<12}")
    
    # 儲存結果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filepath = os.path.join(OUTPUT_DIR, f'leo_dual_filter_{timestamp}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 結果已儲存: {filepath}")
    
    return results


def main():
    if len(sys.argv) == 1:
        scan_all()
    
    elif '--batch' in sys.argv:
        scan_all()
    
    elif '--export' in sys.argv:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filepath = os.path.join(OUTPUT_DIR, f'leo_dual_filter_{timestamp}.json')
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📊 匯出結果 ({len(data)} 筆):")
            for r in data:
                print(f"  {r['code']} {r['name']}: {r['total_score']}分 - {r['action']}")
        else:
            print("❌ 無法找到最新結果，請先執行 scan")
    
    else:
        code = sys.argv[1]
        analyze_stock(code)


if __name__ == '__main__':
    main()
