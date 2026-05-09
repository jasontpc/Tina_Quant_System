# -*- coding: utf-8 -*-
"""
Ray ETF Return Analyzer - 年化報酬率分析模組
計算 15 檔 ETF 的 1年/3年/5年/成立以來年化報酬率
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

# 成立日期（用於計算成立以來報酬）
INCEPTION_DATES = {
    "0050": "2003-06-25",
    "0056": "2007-10-22",
    "00713": "2017-01-23",
    "00891": "2017-09-26",
    "00646": "2018-06-27",
    "00662": "2019-04-23",
    "00757": "2020-09-24",
    "00919": "2022-03-01",
    "00927": "2022-03-01",
    "00915": "2022-03-01",
    "00917": "2022-03-01",
    "00918": "2022-03-01",
    "00920": "2022-03-01",
    "00923": "2022-03-01",
    "00900": "2020-03-19"
}


def calculate_annualized_return(start_price: float, end_price: float, years: float) -> Optional[float]:
    """計算年化報酬率"""
    if start_price <= 0 or years <= 0:
        return None
    return ((end_price / start_price) ** (1 / years) - 1) * 100


def get_etf_return(etf_id: str) -> Dict:
    """計算 ETF 各期間年化報酬率"""
    result = {
        "etf_id": etf_id,
        "1y_return": None,
        "3y_return": None,
        "5y_return": None,
        "since_inception": None,
        "rank_1y": None,
        "rank_3y": None,
        "rank_5y": None
    }
    
    try:
        ticker = yf.Ticker(f"{etf_id}.TW")
        
        # 取 5 年歷史數據
        end_date = datetime.now()
        start_date_5y = end_date - timedelta(days=5 * 365 + 30)
        
        hist = ticker.history(start=start_date_5y.strftime("%Y-%m-%d"))
        
        if hist.empty or len(hist) < 10:
            print(f"  [WARN] {etf_id} insufficient data")
            return result
        
        prices = hist['Close']
        
        # 1 年報酬 (252 交易日)
        if len(prices) >= 252:
            start_1y = prices.iloc[-252]
            end_price = prices.iloc[-1]
            result["1y_return"] = round(calculate_annualized_return(start_1y, end_price, 1), 2)
        
        # 3 年報酬
        if len(prices) >= 252 * 3:
            start_3y = prices.iloc[-252 * 3]
            result["3y_return"] = round(calculate_annualized_return(start_3y, end_price, 3), 2)
        
        # 5 年報酬
        if len(prices) >= 252 * 5:
            start_5y = prices.iloc[-252 * 5]
            result["5y_return"] = round(calculate_annualized_return(start_5y, end_price, 5), 2)
        
        # 成立以來報酬
        inception_str = INCEPTION_DATES.get(etf_id)
        if inception_str:
            inception_date = datetime.strptime(inception_str, "%Y-%m-%d")
            # 找成立後第一個可用的價格
            hist_inception = ticker.history(start=inception_str, end=(inception_date + timedelta(days=30)).strftime("%Y-%m-%d"))
            
            if not hist_inception.empty and len(prices) > 0:
                start_price = hist_inception['Close'].iloc[0]
                end_price = prices.iloc[-1]
                
                years_since = (end_date - inception_date).days / 365.25
                if years_since > 0.5:  # 至少半年
                    result["since_inception"] = round(calculate_annualized_return(start_price, end_price, years_since), 2)
        
        return result
        
    except Exception as e:
        print(f"  [ERROR] {etf_id} return calculation failed: {e}")
        return result


def analyze_returns() -> Dict:
    """執行全面報酬率分析"""
    print("=" * 60)
    print("Ray ETF 年化報酬率分析")
    print("=" * 60)
    
    results = []
    
    for etf in ETF_LIST:
        print(f"\n分析中: {etf}...", end=" ")
        data = get_etf_return(etf)
        results.append(data)
        
        returns_str = []
        if data["1y_return"]:
            returns_str.append(f"1Y:{data['1y_return']:.1f}%")
        if data["3y_return"]:
            returns_str.append(f"3Y:{data['3y_return']:.1f}%")
        if data["5y_return"]:
            returns_str.append(f"5Y:{data['5y_return']:.1f}%")
        
        print(" | ".join(returns_str) if returns_str else "無資料")
    
    # 排名
    for period in ["1y", "3y", "5y"]:
        key = f"{period}_return"
        sorted_list = sorted(
            [r for r in results if r[key] is not None],
            key=lambda x: x[key],
            reverse=True
        )
        for rank, item in enumerate(sorted_list, 1):
            for r in results:
                if r["etf_id"] == item["etf_id"]:
                    r[f"rank_{period}"] = rank
    
    # 輸出排名表
    for period, label in [("1y", "1年"), ("3y", "3年"), ("5y", "5年")]:
        key = f"{period}_return"
        print(f"\n{label}年化報酬排名")
        print("-" * 50)
        
        sorted_list = sorted(
            [r for r in results if r[key] is not None],
            key=lambda x: x[key],
            reverse=True
        )
        
        for rank, item in enumerate(sorted_list, 1):
            print(f"  #{rank} {item['etf_id']}: {item[key]:.2f}%")
    
    # 儲存結果
    output_dir = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"return_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "etf_count": len(results),
            "return_data": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n結果已儲存: {output_file}")
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "etf_count": len(results),
        "return_data": results
    }


if __name__ == "__main__":
    result = analyze_returns()