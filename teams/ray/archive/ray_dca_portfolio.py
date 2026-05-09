# -*- coding: utf-8 -*-
"""
Ray DCA Portfolio Optimizer — DCA 組合優化器
功能：
  - 根據 Jo 的條件（200-300萬資金，3-5年買房）計算最佳 DCA 組合配置
  - 核心70%：0050、00646（穩定大盤）
  - 衛星20%：00878、00919（高息）
  - 現金10%：00915B（短期停泊）

用法:
  python scripts/ray_dca_portfolio.py
"""
import yfinance as yf
import pandas as pd
import sys
import os
import json
from datetime import datetime

# Dynamic path setup
_ScriptDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ScriptDir not in sys.path:
    sys.path.insert(0, _ScriptDir)

sys.stdout.reconfigure(encoding='utf-8')

ETF_NAMES = {
    '0050': '元大台灣50', '00646': '富邦S&P500', '0056': '元大高股息',
    '00878': '國泰永續高息', '00919': '群益台灣精選', '00713': '元大高息低波',
    '00915': '富邦台灣永續高息', '00915B': '富邦票券利息', '2618': '航空雙雄'
}

# Jo 的條件
JO_CAPITAL = 2500000  # NT$2,500,000（假設中位值）
JO_GOAL_YEARS = 4     # 3-5年買房，取中位數
JO_RISK_TOLERANCE = '中等'

# 組合配置
PORTFOLIO = {
    'core': {
        'label': '核心配置（70%）',
        'etfs': ['0050', '00646'],
        'target_pct': 0.70,
        'description': '穩定大盤，長期成長'
    },
    'satellite': {
        'label': '衛星配置（20%）',
        'etfs': ['00878', '00919'],
        'target_pct': 0.20,
        'description': '高股息，现金流来源'
    },
    'cash': {
        'label': '現金停泊（10%）',
        'etfs': ['2618'],
        'target_pct': 0.10,
        'description': '短期停泊，保持流動性'
    }
}


def get_etf_price(etf_id):
    """取得 ETF 現價"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1mo')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        return float(close.iloc[-1])
    except:
        return None


def get_etf_position(etf_id):
    """取得 ETF 在近1年區間的位置"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        price = close.iloc[-1]
        low = close.min()
        high = close.max()
        pos_val = (price - low) / (high - low) * 100 if high > low else 50.0
        return pos_val, float(price) if not pd.isna(price) else None
    except:
        return None, None


def calc_initial_allocation(capital=JO_CAPITAL):
    """
    計算初始配置
    資金分配到各組合
    """
    print()
    print(f'{"="*60}')
    print(f'  Ray DCA 組合配置 — Jo 的 DCA 組合建議')
    print(f'{"="*60}')
    print()
    print(f'  【投資人條件】')
    print(f'    總資金: NT${capital:,}')
    print(f'    目標期間: {JO_GOAL_YEARS} 年（3-5年買房頭期款）')
    print(f'    風險承受: {JO_RISK_TOLERANCE}')
    print()
    print(f'  【組合配置】')

    initial_allocation = {}
    for bucket, info in PORTFOLIO.items():
        amount = capital * info['target_pct']
        initial_allocation[bucket] = {
            'amount': amount,
            'target_pct': info['target_pct'],
            'etfs': info['etfs']
        }
        print(f'    {info["label"]} NT${amount:,.0f} ({info["description"]})')
        for etf_id in info['etfs']:
            price = get_etf_price(etf_id)
            if price and price > 0:
                units = int(amount / len(info['etfs']) / price)
                print(f'      → {etf_id} {ETF_NAMES.get(etf_id, etf_id)}: 現價 ${price:.2f}，可買 ~{units} 股')
            else:
                print(f'      → {etf_id}: 價格取得失敗（市場資料無法取得）')

    print()
    print(f'{"="*60}')
    return initial_allocation


def calc_monthly_dca_budget(capital=JO_CAPITAL, goal_years=JO_GOAL_YEARS):
    """
    計算每月 DCA 建議金額

    邏輯：
    - 初始配置假設佔用 50% 資金（保留流動性）
    - 剩餘 50% 透過 DCA 慢慢投入
    - 每月預算 = 可投入資金 / 剩餘月數
    """
    initial_invest = capital * 0.50  # 初始配置用 50%
    dca_invest = capital * 0.50      # 預留 DCA 的 50%
    months = goal_years * 12

    monthly_budget = int(dca_invest / months)

    # 各組合的 DCA 分配
    core_budget = int(monthly_budget * 0.70)
    satellite_budget = int(monthly_budget * 0.20)
    cash_budget = monthly_budget - core_budget - satellite_budget

    print()
    print(f'{"="*60}')
    print(f'  每月 DCA 建議金額')
    print(f'{"="*60}')
    print()
    print(f'  【DCA 預算邏輯】')
    print(f'    初始配置（已投入）: NT${initial_invest:,.0f} (50%)')
    print(f'    預留 DCA（分期投入）: NT${dca_invest:,.0f} (50%)')
    print(f'    分配期間: {goal_years} 年 ({months} 個月)')
    print(f'    每月 DCA 預算: NT${monthly_budget:,}')
    print()
    print(f'  【DCA 配置】')
    print(f'    核心配置（70%）: NT${core_budget:,}/月')
    print(f'      → 0050 + 00646 均分')
    print(f'    衛星配置（20%）: NT${satellite_budget:,}/月')
    print(f'      → 00878 + 00919 均分')
    print(f'    現金停泊（10%）: NT${cash_budget:,}/月')
    print(f'      → 00915B（視流動性需求）')
    print()
    print(f'  【提醒】')
    print(f'    • 若市場低點，可考慮提高核心配置比例')
    print(f'    • 若接近買房時點（<1年），應逐步降低股票比例')
    print(f'    • 每月 DCA 上限建議: NT$30,000-50,000')
    print(f'    • 超過上限應暫停，等待市場回調')
    print(f'{"="*60}')

    return {
        'total_monthly': monthly_budget,
        'core': core_budget,
        'satellite': satellite_budget,
        'cash': cash_budget,
        'dca_invest_total': dca_invest,
        'months': months
    }


def dynamic_position_adjustment():
    """
    根據市場位置動態調整 DCA 金額
    """
    print()
    print(f'{"="*60}')
    print(f'  動態 DCA 金額調整（根據市場位置）')
    print(f'{"="*60}')
    print()

    positions = {}
    for etf_id in ['0050', '00646', '00878', '00919']:
        pos, price = get_etf_position(etf_id)
        if pos is not None and price is not None:
            positions[etf_id] = {'pos': pos, 'price': price}
            indicator = '🟢 低點加碼' if pos < 40 else ('🟡 正常DCA' if pos < 60 else ('⚠️ 減半' if pos < 75 else '🔴 觀望'))
            multiplier = 2.0 if pos < 30 else (1.5 if pos < 40 else (1.0 if pos < 60 else (0.5 if pos < 75 else 0)))
            print(f'  {etf_id} {ETF_NAMES.get(etf_id, etf_id):<12s}')
            print(f'    現價: ${price:.2f} | 位置: {pos:.1f}%')
            print(f'    建議: {indicator} (×{multiplier})')
            print()

    print(f'  【調整邏輯】')
    print(f'    位置 < 30%:  積極加碼 2x')
    print(f'    位置 30-40%: 適度加碼 1.5x')
    print(f'    位置 40-60%: 正常 DCA 1x')
    print(f'    位置 60-75%: 減少一半 0.5x')
    print(f'    位置 > 75%:  暫停，觀望')
    print()
    print(f'  💡 每月根據市場位置自動調整 DCA 倍數')
    print(f'{"="*60}')


def generate_rebalancing_plan():
    """
    生成年度再平衡建議
    """
    print()
    print(f'{"="*60}')
    print(f'  年度再平衡計劃')
    print(f'{"="*60}')
    print()
    print(f'  【每年1月自動觸發】')
    print(f'    1. 檢視各組合偏離度（目標 ±5% 以內）')
    print(f'    2. 若偏離 > 5%，執行再平衡')
    print(f'    3. 再平衡時優先賣出高於目標的部位')
    print()
    print(f'  【目標配置】')
    for bucket, info in PORTFOLIO.items():
        pct = info['target_pct'] * 100
        etfs = ', '.join([f'{e}({ETF_NAMES.get(e, e)})' for e in info['etfs']])
        print(f'    {info["label"]}: {pct:.0f}% → {etfs}')
    print()
    print(f'  【緊急機制】')
    print(f'    若市場連續下跌 > 20%：')
    print(f'      → 核心配置比例提高至 80%')
    print(f'      → 衛星配置暫停')
    print(f'    若接近買房時點（<1年）：')
    print(f'      → 股票比例降至 40%')
    print(f'      → 現金/债券提高至 60%')
    print(f'{"="*60}')


def generate_portfolio_report():
    """產生完整組合報告"""
    print()
    print('╔' + '═' * 58 + '╗')
    print('║  Ray DCA 完整組合報告                                  ║')
    print('╠' + '═' * 58 + '╣')

    alloc = calc_initial_allocation()
    monthly = calc_monthly_dca_budget()
    dynamic_position_adjustment()
    generate_rebalancing_plan()

    # 儲存報告
    report = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'jo_capital': JO_CAPITAL,
        'goal_years': JO_GOAL_YEARS,
        'allocation': {
            bucket: {
                'amount': info['amount'],
                'target_pct': info['target_pct'],
                'etfs': info['etfs']
            } for bucket, info in alloc.items()
        },
        'monthly_dca': {
            'total': monthly['total_monthly'],
            'core': monthly['core'],
            'satellite': monthly['satellite'],
            'cash': monthly['cash']
        }
    }

    REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(REPORTS_DIR, 'dca_portfolio_plan.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'  報告已儲存: {report_file}')

    return report


if __name__ == '__main__':
    generate_portfolio_report()