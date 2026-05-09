# -*- coding: utf-8 -*-
"""
Ray ETF Yield Analyzer - 殖利率分析模組
分析 15 檔 ETF 的歷史殖利率數據
"""

import yfinance as yf
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 15 檔 ETF 清單
ETF_LIST = [
    "0050", "0056", "00713", "00891", "00646",
    "00662", "00757", "00919", "00927", "00915",
    "00917", "00918", "00920", "00923", "00900"
]

# 費用率 (%)
EXPENSE_RATIOS = {
    "0050": 0.32, "0056": 0.60, "00713": 0.35, "00891": 0.35, "00646": 0.35,
    "00662": 0.35, "00757": 0.40, "00919": 0.35, "00927": 0.35, "00915": 0.35,
    "00917": 0.35, "00918": 0.35, "00920": 0.35, "00923": 0.35, "00900": 0.35
}


def get_dividend_yield(etf_id: str, lookback_days: int = 365) -> Optional[float]:
    """計算殖利率：使用 info.dividendYield（已是非常終端殖利率）"""
    try:
        ticker = yf.Ticker(f"{etf_id}.TW")
        info = ticker.info
        
        if info and 'dividendYield' in info and info['dividendYield']:
            return round(float(info['dividendYield']), 2)
        
        return None
    except Exception as e:
        print(f"  [ERROR] {etf_id} yield calculation failed: {e}")
        return None


def get_historical_yield_series(etf_id: str, years: int = 5) -> List[float]:
    """取得多年歷史殖利率序列（季度估算）"""
    yields = []
    try:
        ticker = yf.Ticker(f"{etf_id}.TW")
        dividends = ticker.dividends
        
        if dividends.empty:
            return []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        recent_divs = dividends[dividends.index >= start_date]
        
        # 計算每季殖利率
        for i in range(4 * years):
            quarter_start = end_date - timedelta(days=(i + 1) * 90)
            quarter_end = end_date - timedelta(days=i * 90)
            
            quarter_divs = recent_divs[
                (recent_divs.index >= quarter_start) & 
                (recent_divs.index < quarter_end)
            ]
            
            if not quarter_divs.empty:
                # 估算季度價格（用期初價格）
                try:
                    price_hist = ticker.history(start=quarter_start.strftime("%Y-%m-%d"), 
                                               end=(quarter_start + timedelta(days=5)).strftime("%Y-%m-%d"))
                    if not price_hist.empty:
                        price = price_hist['Close'].iloc[0]
                        quarter_yield = (quarter_divs.sum() / price) * 100
                        yields.append(round(quarter_yield, 2))
                except:
                    pass
        
        return yields[::-1]  # 由遠到近
    
    except Exception as e:
        return []


def calculate_avg_std(yields: List[float]) -> tuple:
    """計算平均值和標準差"""
    if not yields:
        return None, None
    
    n = len(yields)
    avg = sum(yields) / n
    variance = sum((y - avg) ** 2 for y in yields) / n
    std = variance ** 0.5
    
    return round(avg, 3), round(std, 3)


def determine_trend(yields: List[float]) -> str:
    """判斷殖利率趨勢（基於最近4個季度）"""
    if len(yields) < 2:
        return "不確定"
    
    recent = yields[-4:] if len(yields) >= 4 else yields
    
    first_half = sum(recent[:len(recent)//2]) / (len(recent)//2) if len(recent)//2 > 0 else 0
    second_half = sum(recent[len(recent)//2:]) / (len(recent) - len(recent)//2) if (len(recent) - len(recent)//2) > 0 else 0
    
    change = second_half - first_half
    
    if change > 0.15:
        return "上升"
    elif change < -0.15:
        return "下降"
    else:
        return "穩定"


def analyze_yield(etf_id: str) -> Dict:
    """分析單一 ETF 的殖利率"""
    result = {
        "etf_id": etf_id,
        "current_yield": None,
        "avg_yield_1y": None,
        "avg_yield_3y": None,
        "avg_yield_5y": None,
        "std_dev": None,
        "yield_trend": "不確定",
        "yield_rank": None
    }
    
    # 1. 當前殖利率 (過去12個月)
    current = get_dividend_yield(etf_id, 365)
    result["current_yield"] = current
    
    # 2. 歷史殖利率序列
    yields_5y = get_historical_yield_series(etf_id, 5)
    
    # 3. 各期間平均
    if len(yields_5y) >= 4:
        result["avg_yield_1y"] = round(sum(yields_5y[-4:]) / 4, 2)
    if len(yields_5y) >= 12:
        result["avg_yield_3y"] = round(sum(yields_5y[-12:]) / 12, 2)
    if len(yields_5y) >= 20:
        result["avg_yield_5y"] = round(sum(yields_5y[-20:]) / 20, 2)
    
    # 4. 標準差
    avg, std = calculate_avg_std(yields_5y[-20:] if len(yields_5y) >= 20 else yields_5y)
    result["std_dev"] = std
    
    # 5. 趨勢
    result["yield_trend"] = determine_trend(yields_5y)
    
    # 6. 費用率
    result["expense_ratio"] = EXPENSE_RATIOS.get(etf_id, 0.35)
    
    return result


def run_yield_analysis() -> Dict:
    """執行全面殖利率分析"""
    print("=" * 60)
    print("Ray ETF 殖利率分析")
    print("=" * 60)
    
    results = []
    
    for etf in ETF_LIST:
        print(f"\n分析中: {etf}...", end=" ")
        data = analyze_yield(etf)
        results.append(data)
        print(f"當前殖利率: {data['current_yield']}%")
    
    # 排名（按當前殖利率）
    sorted_by_yield = sorted(
        [r for r in results if r["current_yield"] is not None],
        key=lambda x: x["current_yield"],
        reverse=True
    )
    
    for rank, item in enumerate(sorted_by_yield, 1):
        for r in results:
            if r["etf_id"] == item["etf_id"]:
                r["yield_rank"] = rank
    
    # 輸出排名
    print("\n" + "=" * 60)
    print("殖利率排名（高→低）")
    print("=" * 60)
    print(f"{'排名':<6}{'ETF':<8}{'當前殖利率':<12}{'1年平均':<10}{'3年平均':<10}{'5年平均':<10}{'標準差':<10}{'趨勢':<8}")
    print("-" * 80)
    
    for item in sorted_by_yield:
        print(f"{item['yield_rank']:<6}{item['etf_id']:<8}"
              f"{item['current_yield'] or 'N/A':<12}"
              f"{item['avg_yield_1y'] or 'N/A':<10}"
              f"{item['avg_yield_3y'] or 'N/A':<10}"
              f"{item['avg_yield_5y'] or 'N/A':<10}"
              f"{item['std_dev'] or 'N/A':<10}"
              f"{item['yield_trend']:<8}")
    
    # 儲存結果
    output_dir = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"yield_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "etf_count": len(results),
            "yield_ranking": sorted_by_yield,
            "all_data": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n結果已儲存: {output_file}")
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "etf_count": len(results),
        "yield_ranking": sorted_by_yield,
        "all_data": results
    }


if __name__ == "__main__":
    result = run_yield_analysis()