"""
Ray 大盤階段分析模組 - TWII 市場階段識別與策略建議
====================================================
功能：
  - 識別歷史上的不同市場階段
  - 每個階段的特徵（多頭/空頭/震盪）
  - 每個階段適合的策略建議

Author: Ray Team
Date: 2026-04-24
"""

import json
from datetime import datetime
from pathlib import Path

# ======================
# 絕對路徑設定
# ======================
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray")
REPORTS_DIR = BASE_DIR / "reports"

# ======================
# 市場階段定義
# ======================

PHASES = {
    "bull_2024_2026": {
        "id": "bull_2024_2026",
        "period": "2024-2026",
        "twii_range": "15000-38932",
        "characteristic": "多頭市場 - AI熱潮、資金行情",
        "best_strategy": "Buy&Hold / 成長股",
        "dca_return": "低",
        "dca_vs_bh": "DCA 表現不如 B&H（市場持續上漲，DCA 成本墊高）",
        "description": """
2024-2026 年是多頭市場，Tina 系統在這段時間表現優異。
主因為：
1. AI 概念股帶動台積電等權值股大漲
2. 台灣出口暢旺，半導體供應鏈景氣佳
3. 外資持續流入，推升指數

此時期 BUY&HOLD 表現最好，但 DCA 仍能提供穩定報酬。
適合積極操作，搭配成長型 ETF（如 0050、00662）。
        """,
        "recommended_etfs": ["0050", "00662", "00881"],
        "risk_level": "中等",
        "notes": "高點适当减仓，避免追高",
    },

    "bear_2022": {
        "id": "bear_2022",
        "period": "2022",
        "twii_range": "12000-15000",
        "characteristic": "空頭市場 - 升息循環、通貨膨脹",
        "best_strategy": "DCA / 定時定額",
        "dca_return": "高",
        "dca_vs_bh": "DCA 顯著優於 B&H（低檔持續買入攤平成本）",
        "description": """
2022 年是空頭市場，美國聯準會暴力升息對抗通膨。
TWII 從 18600 高點跌至 13800 低點，跌約 25%。

此時期 DCA 策略表現最好：
- 每月固定買入，持續在低點累積單位數
- 當市場回升時，DCA 投資者擁有更多單位，獲利更佳

適合使用價值型ETF（如 0056、00713），搭配 DCA。
        """,
        "recommended_etfs": ["0056", "00713", "00878"],
        "risk_level": "高",
        "notes": "严格止损，避免 ALL IN",
    },

    "covid_2020": {
        "id": "covid_2020",
        "period": "2020",
        "twii_range": "8500-15000",
        "characteristic": "疫情爆發 - V型復甦",
        "best_strategy": "DCA / 危機入市",
        "dca_return": "高",
        "dca_vs_bh": "DCA 略優於 B&H（低點買入，成本優勢明顯）",
        "description": """
2020 年 COVID-19 疫情爆發，TWII 在 2020/3 跌至 8500 低點。
之後 V 型反轉，2020/12 回升至 14000，漲幅逾 60%。

DCA 在這段時間表現突出：
- 疫情期間低檔持續買入，累積大量單位
- V 型回升時，享受超額報酬

適合使用市值型 ETF（如 0050），搭配紀律性 DCA。
危機入市者更可考慮一次性重倉（但需嚴控風險）。
        """,
        "recommended_etfs": ["0050", "0056", "00692"],
        "risk_level": "高",
        "notes": "危機入市时机，关键在纪律",
    },

    "trade_war_2019": {
        "id": "trade_war_2019",
        "period": "2019",
        "twii_range": "9500-12000",
        "characteristic": "美中貿易戰 - 震盪整理",
        "best_strategy": "DCA / 區間操作",
        "dca_return": "中",
        "dca_vs_bh": "DCA 與 B&H 差不多（市場無明顯趨勢）",
        "description": """
2019 年美中貿易談判反覆，市場情緒不穩定。
TWII 在 9500-12000 區間震盪，沒有明顯趨勢。

此時期 DCA 和 B&H 表現差不多。
適合價值型投資，挑选被低估的股票或 ETF。
關注產業龍頭（如台積電），長期持有。
        """,
        "recommended_etfs": ["0050", "0056", "00878"],
        "risk_level": "中",
        "notes": "區間操作，高點賣出部分",
    },

    "rate_hike_2023": {
        "id": "rate_hike_2023",
        "period": "2023 上半年",
        "twii_range": "14000-17000",
        "characteristic": "升息尾聲 - 市場忐忑",
        "best_strategy": "DCA / 保守操作",
        "dca_return": "中",
        "dca_vs_bh": "DCA 略優於 B&H（利率高檔，股市震盪）",
        "description": """
2023 年上半年，美國 Fed 持續升息對抗通膨。
市場在高利率環境下震盪，TWII 在 14000-17000 整理。

DCA 在此時期表現適中：
- 每月固定買入，避免選時風險
- 低點持續累積，等待降息行情

適合使用高股息的 ETF（如 0056、00878），
搭配保守的 DCA 策略。
        """,
        "recommended_etfs": ["0056", "00878", "00713"],
        "risk_level": "中",
        "notes": "等待降息信號，可考虑加码",
    },

    "recovery_2021": {
        "id": "recovery_2021",
        "period": "2021",
        "twii_range": "15000-18000",
        "characteristic": "疫情後復甦 - 景氣擴張",
        "best_strategy": "Buy&Hold / 成長型",
        "dca_return": "低",
        "dca_vs_bh": "DCA 不如 B&H（市場持續上漲）",
        "description": """
2021 年疫情後復甦，疫苗開打、全球景氣擴張。
TWII 從 15000 漲至 18000，漲幅 20%。

此時期 B&H 表現最好，DCA 反而因為不斷在高點買入而墊高成本。
建議：
- 成長型投資人可減少 DCA，增加一次性投資
- 保守投資人維持 DCA，但可减少投入金额
- 关注涨多板块，适度获利了结
        """,
        "recommended_etfs": ["0050", "00662", "00881"],
        "risk_level": "中",
        "notes": "涨多考虑减码，避免追高",
    },
}

# ======================
# 策略建議矩陣
# ======================

STRATEGY_MATRIX = {
    "多頭": {
        "description": "市場持續創高，投資人情緒樂觀",
        "recommended_strategies": ["Buy&Hold", "成長股配置", "定期定額但减少金额"],
        "avoid_strategies": ["過度樂觀追高", "过度集中單一股"],
        "risk_level": "中",
        "key_metrics": {
            "TWII": ">20000",
            "MA20": "多頭排列",
            "RSI": ">60",
        },
    },
    "空頭": {
        "description": "市場持續破底，投資人情緒悲觀",
        "recommended_strategies": ["DCA定時定額", "價值型ETF", "危機入市"],
        "avoid_strategies": ["恐慌性拋售", "ALL IN"],
        "risk_level": "高",
        "key_metrics": {
            "TWII": "<15000",
            "MA20": "空頭排列",
            "RSI": "<40",
        },
    },
    "震盪": {
        "description": "市場區間整理，沒有明顯趨勢",
        "recommended_strategies": ["區間操作", "DCA", "價值投資"],
        "avoid_strategies": ["過度頻繁交易", "追高殺低"],
        "risk_level": "中",
        "key_metrics": {
            "TWII": "15000-20000區間",
            "MA20": "糾結",
            "RSI": "40-60",
        },
    },
    "復甦": {
        "description": "市場從低點反彈，景氣開始好轉",
        "recommended_strategies": ["DCA", "買入持有", "成長型ETF"],
        "avoid_strategies": ["過早離場", "過度保守"],
        "risk_level": "中低",
        "key_metrics": {
            "TWII": "突破MA20",
            "MA20": "由下往上穿越",
            "RSI": "40-50→60",
        },
    },
}

# ======================
# 工具函數
# ======================

def get_current_phase(twii_price: float = None, period: str = None) -> dict:
    """
    根據價格或時期，回傳建議的市場階段
    如果有即時價格，优先使用
    """
    if period:
        for phase_id, phase in PHASES.items():
            if period in phase['period']:
                return phase

    # 根據價格區間判斷
    if twii_price:
        if twii_price > 30000:
            return PHASES['bull_2024_2026']
        elif twii_price > 20000:
            return PHASES['bull_2024_2026']
        elif twii_price < 15000:
            return PHASES['bear_2022']

    return {
        "id": "unknown",
        "characteristic": "市場階段不明",
        "best_strategy": "保守操作",
        "dca_return": "未知",
        "description": "數據不足，無法判斷市場階段。建議保守操作，關注基本面變化。",
        "recommended_etfs": ["0050", "0056"],
        "risk_level": "未知",
        "notes": "等待更多數據",
    }

def get_strategy_for_phase(phase_name: str) -> dict:
    """根據階段名稱取得策略建議"""
    # 嘗試關鍵字匹配
    for key, strategy in STRATEGY_MATRIX.items():
        if key in phase_name or phase_name in key:
            return strategy
    return STRATEGY_MATRIX["震盪"]  # 預設值

def generate_phase_report(phase_id: str = None) -> dict:
    """生成階段分析報告"""
    if phase_id:
        if phase_id in PHASES:
            phase = PHASES[phase_id]
            strategy = get_strategy_for_phase(phase['characteristic'].split('-')[0].strip())
            return {
                'phase': phase,
                'strategy': strategy,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    # 全市場階段報告
    all_phases = []
    for pid, phase in PHASES.items():
        strategy = get_strategy_for_phase(phase['characteristic'].split('-')[0].strip())
        all_phases.append({
            'phase': phase,
            'strategy': strategy,
        })

    return {
        'all_phases': all_phases,
        'strategy_matrix': STRATEGY_MATRIX,
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': 'TWII 市場階段分析報告',
    }

def save_phase_report(report: dict, filename: str = None):
    """儲存階段報告"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"twii_phases_{timestamp}.json"

    filepath = REPORTS_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 儲存最新報告
    latest_path = REPORTS_DIR / "twii_phases_latest.json"
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Report saved: {filepath}")
    return str(filepath)

def get_phase_summary_text():
    """Get phase summary as text (ASCII-safe)"""
    lines = []
    lines.append("=" * 60)
    lines.append("TWII Market Phase Analysis Summary (ASCII Mode)")
    lines.append("=" * 60)

    for phase_id, phase in PHASES.items():
        lines.append(f"\n[{phase['period']}] {phase['characteristic']}")
        lines.append(f"  TWII Range: {phase['twii_range']}")
        lines.append(f"  Best Strategy: {phase['best_strategy']}")
        lines.append(f"  DCA Performance: {phase['dca_return']}")
        lines.append(f"  Risk Level: {phase['risk_level']}")
        lines.append(f"  Recommended ETFs: {', '.join(phase['recommended_etfs'])}")

    lines.append("\n" + "=" * 60)
    lines.append("Strategy Matrix:")
    for name, strategy in STRATEGY_MATRIX.items():
        lines.append(f"\n  [{name}]")
        lines.append(f"    Description: {strategy['description']}")
        lines.append(f"    Recommended: {', '.join(strategy['recommended_strategies'])}")
        lines.append(f"    Avoid: {', '.join(strategy['avoid_strategies'])}")
    lines.append("=" * 60)
    return '\n'.join(lines)

def print_phase_summary():
    """Print phase summary"""
    try:
        print(get_phase_summary_text())
    except UnicodeEncodeError:
        # Fallback: just show key info
        print("TWII Market Phase Analysis")
        for phase_id, phase in PHASES.items():
            print(f"{phase['period']}: Best={phase['best_strategy']}, DCA={phase['dca_return']}, Risk={phase['risk_level']}")

# ======================
# 入口點
# ======================

if __name__ == "__main__":
    print("Ray Market Phase Analysis Started")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Generate full report
    report = generate_phase_report()

    # Print summary
    print_phase_summary()

    # Save report
    filepath = save_phase_report(report)

    print("\nPhase analysis complete!")
    print(f"Report: {filepath}")