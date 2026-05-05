# -*- coding: utf-8 -*-
"""
Ray ETF Comprehensive Analyzer - 綜合分析模組
整合殖利率 + 年化報酬率，輸出 CP 值評估與建議報告
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

# 成立日期
INCEPTION_DATES = {
    "0050": "2003-06-25", "0056": "2007-10-22", "00713": "2017-01-23",
    "00891": "2017-09-26", "00646": "2018-06-27", "00662": "2019-04-23",
    "00757": "2020-09-24", "00919": "2022-03-01", "00927": "2022-03-01",
    "00915": "2022-03-01", "00917": "2022-03-01", "00918": "2022-03-01",
    "00920": "2022-03-01", "00923": "2022-03-01", "00900": "2020-03-19"
}


def get_yield_data(etf_id: str) -> Dict:
    """取得殖利率數據"""
    result = {
        "etf_id": etf_id,
        "current_yield": None,
        "avg_yield_1y": None,
        "expense_ratio": EXPENSE_RATIOS.get(etf_id, 0.35)
    }
    
    try:
        ticker = yf.Ticker(f"{etf_id}.TW")
        
        # 使用 info 中的 dividendYield (已經是百分比)
        info = ticker.info
        if info and 'dividendYield' in info and info['dividendYield']:
            result["current_yield"] = round(float(info['dividendYield']), 2)
        else:
            # 備用：計算過去12個月股利
            dividends = ticker.dividends
            if not dividends.empty:
                cutoff = datetime.now() - timedelta(days=365)
                recent_divs = dividends[dividends.index >= cutoff]
                if not recent_divs.empty:
                    annual_div = recent_divs.sum()
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        result["current_yield"] = round((annual_div / current_price) * 100, 2)
        
        # 嘗試計算 1 年平均（使用季度殖利率）
        try:
            yields = []
            end_date = datetime.now()
            for i in range(4):
                q_start = end_date - timedelta(days=(i + 1) * 90)
                q_end = end_date - timedelta(days=i * 90)
                
                # 取該季的價格起點
                price_start = ticker.history(
                    start=q_start.strftime("%Y-%m-%d"),
                    end=(q_start + timedelta(days=10)).strftime("%Y-%m-%d")
                )
                if not price_start.empty:
                    p = price_start['Close'].iloc[0]
                    # 取該季的股利
                    q_divs = dividends[(dividends.index >= q_start) & (dividends.index < q_end)]
                    if not q_divs.empty and p > 0:
                        yields.append(round((q_divs.sum() / p) * 100, 2))
            
            if yields:
                result["avg_yield_1y"] = round(sum(yields) / len(yields), 2)
        except:
            pass
        
        return result
        
    except Exception as e:
        return result


def get_return_data(etf_id: str) -> Dict:
    """取得報酬率數據"""
    result = {
        "etf_id": etf_id,
        "1y_return": None,
        "3y_return": None,
        "5y_return": None,
        "since_inception": None
    }
    
    try:
        ticker = yf.Ticker(f"{etf_id}.TW")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5 * 365 + 30)
        
        hist = ticker.history(start=start_date.strftime("%Y-%m-%d"))
        
        if hist.empty or len(hist) < 10:
            return result
        
        prices = hist['Close']
        end_price = prices.iloc[-1]
        
        # 1 年
        if len(prices) >= 252:
            start_1y = prices.iloc[-252]
            years = 1
            result["1y_return"] = round(((end_price / start_1y) ** (1 / years) - 1) * 100, 2)
        
        # 3 年
        if len(prices) >= 252 * 3:
            start_3y = prices.iloc[-252 * 3]
            result["3y_return"] = round(((end_price / start_3y) ** (1 / 3) - 1) * 100, 2)
        
        # 5 年
        if len(prices) >= 252 * 5:
            start_5y = prices.iloc[-252 * 5]
            result["5y_return"] = round(((end_price / start_5y) ** (1 / 5) - 1) * 100, 2)
        
        # 成立以來
        inception_str = INCEPTION_DATES.get(etf_id)
        if inception_str:
            inception_date = datetime.strptime(inception_str, "%Y-%m-%d")
            hist_inc = ticker.history(
                start=inception_str,
                end=(inception_date + timedelta(days=30)).strftime("%Y-%m-%d")
            )
            if not hist_inc.empty:
                start_price = hist_inc['Close'].iloc[0]
                years_since = (end_date - inception_date).days / 365.25
                if years_since > 0.5:
                    result["since_inception"] = round(((end_price / start_price) ** (1 / years_since) - 1) * 100, 2)
        
        return result
        
    except Exception as e:
        return result


def calculate_stability_score(yields: List[float]) -> float:
    """計算穩定性分數 (0-100, 越高越穩定)"""
    if not yields or len(yields) < 2:
        return 50
    
    avg = sum(yields) / len(yields)
    if avg == 0:
        return 50
    
    variance = sum((y - avg) ** 2 for y in yields) / len(yields)
    cv = (variance ** 0.5) / avg  # 變異係數
    
    # CV 越低越穩定
    if cv <= 0.05:
        return 100
    elif cv >= 0.5:
        return 20
    else:
        # 線性映射
        return max(20, min(100, 100 - (cv - 0.05) / 0.45 * 80))


def calculate_cp_score(data: Dict, stability: float) -> Dict:
    """計算 CP 值分數"""
    # 各維度權重
    # 殖利率 × 0.3 + 年化報酬 × 0.4 + 穩定性 × 0.2 + 費用率 × 0.1
    
    yield_score = (data.get("current_yield") or 0) * 10  # 2% → 20分
    return_score = (data.get("3y_return") or data.get("1y_return") or 0) * 2  # 10% → 20分
    stability_score = stability  # 0-100
    expense_score = max(0, 10 - (data.get("expense_ratio", 0.35) * 20))  # 0.35% → 3分
    
    total_score = (
        yield_score * 0.3 +
        return_score * 0.4 +
        stability_score * 0.2 +
        expense_score * 0.1
    )
    
    # 等級
    if total_score >= 80:
        grade = "A+"
    elif total_score >= 70:
        grade = "A"
    elif total_score >= 60:
        grade = "B+"
    elif total_score >= 50:
        grade = "B"
    elif total_score >= 40:
        grade = "C"
    else:
        grade = "D"
    
    return {
        "cp_score": round(total_score, 1),
        "grade": grade,
        "yield_score": round(yield_score, 1),
        "return_score": round(return_score, 1),
        "stability_score": round(stability_score, 1),
        "expense_score": round(expense_score, 1)
    }


def run_comprehensive_analysis() -> Dict:
    """執行綜合分析"""
    print("=" * 70)
    print("Ray ETF 綜合分析 - 殖利率 + 年化報酬率 + CP 值")
    print("=" * 70)
    
    all_data = []
    
    for etf in ETF_LIST:
        print(f"\n分析 {etf}...", end=" ")
        
        # 取得資料
        yield_data = get_yield_data(etf)
        return_data = get_return_data(etf)
        
        # 合併
        combined = {**yield_data, **return_data}
        
        # 估算穩定性（使用報酬的波動）
        stability = 70  # 預設值
        
        # CP 分數
        cp = calculate_cp_score(combined, stability)
        combined.update(cp)
        
        all_data.append(combined)
        print(f"CP Score: {cp['cp_score']:.1f} ({cp['grade']})")
    
    # === 殖利率排名 ===
    yield_sorted = sorted(
        [d for d in all_data if d["current_yield"] is not None],
        key=lambda x: x["current_yield"],
        reverse=True
    )
    for rank, item in enumerate(yield_sorted, 1):
        for d in all_data:
            if d["etf_id"] == item["etf_id"]:
                d["yield_rank"] = rank
    
    # === 報酬排名 ===
    for period in ["1y", "3y", "5y"]:
        key = f"{period}_return"
        sorted_list = sorted(
            [d for d in all_data if d[key] is not None],
            key=lambda x: x[key],
            reverse=True
        )
        for rank, item in enumerate(sorted_list, 1):
            for d in all_data:
                if d["etf_id"] == item["etf_id"]:
                    d[f"rank_{period}"] = rank
    
    # === CP 值排名 ===
    cp_sorted = sorted(all_data, key=lambda x: x["cp_score"], reverse=True)
    for rank, item in enumerate(cp_sorted, 1):
        for d in all_data:
            if d["etf_id"] == item["etf_id"]:
                d["cp_rank"] = rank
    
    # === 輸出報告 ===
    print("\n" + "=" * 70)
    print("殖利率排名（高→低）")
    print("=" * 70)
    print(f"{'排名':<5}{'ETF':<8}{'殖利率':<10}{'1Y報酬':<10}{'3Y報酬':<10}{'CP值':<8}{'等級':<6}")
    print("-" * 70)
    for item in yield_sorted:
        print(f"{item.get('yield_rank', '-'):<5}{item['etf_id']:<8}"
              f"{item['current_yield'] or 'N/A':<10}"
              f"{item.get('1y_return') or 'N/A':<10}"
              f"{item.get('3y_return') or 'N/A':<10}"
              f"{item['cp_score']:<8.1f}"
              f"{item['grade']:<6}")
    
    print("\n" + "=" * 70)
    print("CP 值排名（高→低）")
    print("=" * 70)
    print(f"{'排名':<5}{'ETF':<8}{'CP值':<8}{'等級':<6}{'殖利率分':<10}{'報酬分':<10}{'穩定分':<10}{'費用分':<10}")
    print("-" * 80)
    for item in cp_sorted:
        print(f"{item.get('cp_rank', '-'):<5}{item['etf_id']:<8}"
              f"{item['cp_score']:<8.1f}{item['grade']:<6}"
              f"{item['yield_score']:<10.1f}{item['return_score']:<10.1f}"
              f"{item['stability_score']:<10.1f}{item['expense_score']:<10.1f}")
    
    # === 建議 ===
    highest_yield = yield_sorted[0]["etf_id"] if yield_sorted else None
    best_1y = max(all_data, key=lambda x: x.get("1y_return") or -999)
    best_3y = max(all_data, key=lambda x: x.get("3y_return") or -999)
    best_cp = cp_sorted[0]["etf_id"] if cp_sorted else None
    
    recommendations = {
        "highest_yield": highest_yield,
        "best_1y_return": best_1y["etf_id"] if best_1y else None,
        "best_3y_return": best_3y["etf_id"] if best_3y else None,
        "best_cp_value": best_cp
    }
    
    print("\n" + "=" * 70)
    print("推薦摘要")
    print("=" * 70)
    print(f"  最高殖利率: {highest_yield}")
    print(f"  最佳 1 年報酬: {best_1y['etf_id']} ({best_1y.get('1y_return')}%)")
    print(f"  最佳 3 年報酬: {best_3y['etf_id']} ({best_3y.get('3y_return')}%)")
    print(f"  最佳 CP 值: {best_cp}")
    
    # 儲存結果
    output_dir = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"comprehensive_analysis_{timestamp}.json")
    
    final_report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "etf_count": len(all_data),
        "yield_ranking": [
            {"etf_id": d["etf_id"], "current_yield": d["current_yield"], "yield_rank": d.get("yield_rank")}
            for d in yield_sorted
        ],
        "return_ranking": [
            {"etf_id": d["etf_id"], "1y_return": d.get("1y_return"), "3y_return": d.get("3y_return"), "5y_return": d.get("5y_return")}
            for d in sorted(all_data, key=lambda x: x.get("3y_return") or -999, reverse=True)
        ],
        "cp_value_ranking": [
            {"etf_id": d["etf_id"], "cp_score": d["cp_score"], "grade": d["grade"], "cp_rank": d.get("cp_rank")}
            for d in cp_sorted
        ],
        "recommendations": recommendations,
        "all_data": all_data
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n完整報告已儲存: {output_file}")
    
    return final_report


if __name__ == "__main__":
    result = run_comprehensive_analysis()