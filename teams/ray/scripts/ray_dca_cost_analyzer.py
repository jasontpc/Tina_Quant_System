# -*- coding: utf-8 -*-
"""
Ray DCA Cost Analyzer — DCA 成本分析模組
功能：
  - 分析 DCA 的真實成本
  - 計算手續費、交易成本、機會成本
  - 評估每檔 ETF 的「CP值」

用法:
  python scripts/ray_dca_cost_analyzer.py 0050
  python scripts/ray_dca_cost_analyzer.py --all
"""
import yfinance as yf
import pandas as pd
import numpy as np
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
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00919': '群益台灣精選', '00713': '元大高息低波', '00646': '富邦S&P500',
    '00662': '富邦NASDAQ', '00757': '統一大FANG+'
}

# 管理費（年度%）
EXPENSE_RATIOS = {
    '0050': 0.32, '0056': 0.35, '00878': 0.35, '00919': 0.42,
    '00713': 0.40, '00646': 0.56, '00662': 0.60, '00757': 0.70
}

# 預設配息率（年化%）
DIVIDEND_YIELDS = {
    '0050': 2.0, '0056': 4.5, '00878': 4.8, '00919': 5.2,
    '00713': 5.0, '00646': 1.4, '00662': 0.8, '00757': 0.5
}

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')


def calc_trading_cost(monthly_amount=5000, years=5, fee_rate=0.001425):
    """
    計算交易成本（手續費 + 交易稅）
    台股：手續費 0.1425%，卖出另加 0.1% 交易稅（ETF免稅）

    DCA 只買不入，ETF 在台灣一般免徵交易稅，主要為手續費
    假設：買入時 0.1425% x 2（來回）= 0.285%
    """
    trades_per_year = 12  # 月配
    total_trades = trades_per_year * years
    cost_per_trade = monthly_amount * fee_rate * 2  # 買賣來回
    total_cost = cost_per_trade * total_trades
    return {
        'per_trade': round(cost_per_trade, 0),
        'total_trades': total_trades,
        'total_trading_cost': round(total_cost, 0),
        'avg_cost_per_month': round(cost_per_trade, 0)
    }


def calc_expense_cost(total_invested=300000, expense_ratio=0.32, years=5):
    """
    計算管理費成本（年度費用率）
    """
    avg_invested = total_invested / 2  # 平均持有金額
    annual_expense = avg_invested * (expense_ratio / 100)
    total_expense = annual_expense * years
    return {
        'annual_expense': round(annual_expense, 0),
        'total_expense': round(total_expense, 0),
        'expense_ratio_pct': expense_ratio
    }


def calc_opportunity_cost(total_invested=300000, years=5, cash_rate=0.015):
    """
    計算機會成本（持有 vs 現金）
    假設現金利率 1.5%（銀行定存）
    """
    avg_invested = total_invested / 2
    annual_opp = avg_invested * cash_rate
    total_opp = annual_opp * years
    return {
        'annual_opp_cost': round(annual_opp, 0),
        'total_opp_cost': round(total_opp, 0),
        'cash_rate': cash_rate
    }


def calc_inflation_adjustment(final_value=400000, years=5, inflation=0.025):
    """計算通貨膨脹調整後的真實報酬"""
    real_value = final_value / ((1 + inflation) ** years)
    return {
        'nominal_value': final_value,
        'real_value': round(real_value, 0),
        'inflation_pct': inflation * 100,
        'purchasing_power_loss': round(final_value - real_value, 0)
    }


def analyze_etf_cost(etf_id, monthly_amount=5000, years=5, total_invested=None):
    """完整成本分析"""
    name = ETF_NAMES.get(etf_id, etf_id)

    if total_invested is None:
        total_invested = monthly_amount * 12 * years

    exp_ratio = EXPENSE_RATIOS.get(etf_id, 0.4)
    div_yield = DIVIDEND_YIELDS.get(etf_id, 2.0)

    # 1. 交易成本
    trading = calc_trading_cost(monthly_amount, years)

    # 2. 管理費成本
    expense = calc_expense_cost(total_invested, exp_ratio, years)

    # 3. 機會成本
    opp = calc_opportunity_cost(total_invested, years)

    # 4. 總成本
    total_cost = trading['total_trading_cost'] + expense['total_expense']
    effective_cost_rate = (total_cost / total_invested) * 100 if total_invested > 0 else 0

    # 5. 配息收益
    annual_div = total_invested * (div_yield / 100) / 2  # 平均持有
    total_div = annual_div * years

    # 6. CP值計算
    # CP值 = (總報酬 - 總成本) / 總成本 = 效益/成本比
    # 假設年化報酬 8%，算最終價值
    annual_return = 0.08  # 8% 年化假設
    final_value = total_invested * ((1 + annual_return) ** years)
    net_return = final_value - total_invested - total_cost + total_div
    cp_ratio = net_return / total_cost if total_cost > 0 else 0

    return {
        'etf_id': etf_id,
        'name': name,
        'assumptions': {
            'monthly_amount': monthly_amount,
            'years': years,
            'total_invested': total_invested
        },
        'trading_cost': trading,
        'expense_cost': expense,
        'opportunity_cost': opp,
        'total_cost': {
            'trading': trading['total_trading_cost'],
            'expense': expense['total_expense'],
            'total': round(total_cost, 0)
        },
        'effective_cost_rate_pct': round(effective_cost_rate, 2),
        'dividend_income': {
            'annual': round(annual_div, 0),
            'total': round(total_div, 0),
            'yield_pct': div_yield
        },
        'estimated_outcome': {
            'final_value': round(final_value, 0),
            'net_return': round(net_return, 0),
            'cp_ratio': round(cp_ratio, 2)
        }
    }


def print_cost_report(r):
    """輸出成本報告"""
    name = r['name']
    etf_id = r['etf_id']
    a = r['assumptions']
    tc = r['total_cost']
    div = r['dividend_income']
    out = r['estimated_outcome']

    print()
    print(f'{"="*60}')
    print(f'  DCA 成本分析 — {name} ({etf_id})')
    print(f'{"="*60}')
    print()
    print(f'  【假設條件】')
    print(f'    每月金額: ${a["monthly_amount"]:,}')
    print(f'    持有期間: {a["years"]} 年')
    print(f'    總投入: ${a["total_invested"]:,.0f}')
    print()
    print(f'  【成本細項】')
    print(f'    交易手續費: ${r["trading_cost"]["total_trading_cost"]:,.0f}')
    print(f'      (每筆 ${r["trading_cost"]["per_trade"]:,}，共 {r["trading_cost"]["total_trades"]} 次)')
    print(f'    管理費成本: ${r["expense_cost"]["total_expense"]:,.0f}')
    print(f'      (年度 {r["expense_cost"]["expense_ratio_pct"]}%，年均 ${r["expense_cost"]["annual_expense"]:,})')
    print(f'    機會成本(現金): ${r["opportunity_cost"]["total_opp_cost"]:,.0f}')
    print(f'      (假設定存利率 {r["opportunity_cost"]["cash_rate"]*100:.1f}%)')
    print()
    print(f'  【總成本】')
    print(f'    總成本: ${tc["total"]:,.0f}')
    print(f'    有效成本率: {r["effective_cost_rate_pct"]:.2f}%')
    print()
    print(f'  【配息收益】')
    print(f'    年化配息率: {div["yield_pct"]:.1f}%')
    print(f'    預估年均配息: ${div["annual"]:,.0f}')
    print(f'    預估5年總配息: ${div["total"]:,.0f}')
    print()
    print(f'  【預估成果（假設年化報酬 8%）】')
    print(f'    最終帳面價值: ${out["final_value"]:,.0f}')
    print(f'    淨報酬(扣成本+配息): ${out["net_return"]:,.0f}')
    print(f'    CP值(效益/成本): {out["cp_ratio"]:.2f}x')
    print()
    print(f'  【CP值評估】')
    if out['cp_ratio'] >= 3.0:
        grade = '🟢 極高CP — 成本極低，長期複利效果顯著'
    elif out['cp_ratio'] >= 2.0:
        grade = '🟡 高CP — 成本適中，適合長期 DCA'
    elif out['cp_ratio'] >= 1.0:
        grade = '⚪ 普通CP — 成本合理，需配合市場表現'
    else:
        grade = '🟠 低CP — 成本偏高，需謹慎考慮'
    print(f'    {grade}')
    print()
    print(f'  【建議】')
    if r['effective_cost_rate_pct'] < 1.5:
        print(f'    ✅ 成本競爭力佳，費用率 {r["expense_cost"]["expense_ratio_pct"]}% 屬於低水位')
    elif r['effective_cost_rate_pct'] < 2.5:
        print(f'    ⚠️ 成本中等，長期需注意費用侵蝕')
    else:
        print(f'    ❌ 成本偏高，建議評估其他標的')
    print(f'{"="*60}')


def rank_all_etfs(core_etfs=None):
    """所有 ETF 成本排名"""
    if core_etfs is None:
        core_etfs = ['0050', '0056', '00878', '00919', '00713', '00646']

    print()
    print('=' * 60)
    print('  Ray DCA 成本 CP 值排名')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d")}')
    print('=' * 60)

    results = []
    for etf_id in core_etfs:
        try:
            r = analyze_etf_cost(etf_id, monthly_amount=5000, years=5)
            results.append(r)
        except Exception as e:
            print(f'  {etf_id}: 分析失敗 ({e})')

    results.sort(key=lambda x: x['estimated_outcome']['cp_ratio'], reverse=True)

    print()
    print(f'  {"ETF":<8s} {"名稱":<12s} {"總成本":>8s} {"有效成本%":>9s} {"年化配息":>7s} {"CP值":>6s}')
    print(f'  {"-"*8} {"-"*12} {"-"*8} {"-"*9} {"-"*7} {"-"*6}')

    for r in results:
        tc = r['total_cost']
        out = r['estimated_outcome']
        div = r['dividend_income']
        print(f'  {r["etf_id"]:<8s} {r["name"][:10]:<12s} ${tc["total"]:>7,.0f} {r["effective_cost_rate_pct"]:>8.2f}% {div["yield_pct"]:>6.1f}% {out["cp_ratio"]:>5.2f}x')

    print()
    print(f'  💡 CP值說明: (淨報酬 / 總成本)，越高代表成本效益越好')
    print(f'     CP > 3.0 = 極優秀 | 2.0-3.0 = 佳 | 1.0-2.0 = 普通 | < 1.0 = 偏差')
    print('=' * 60)

    # 儲存
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(REPORTS_DIR, 'dca_cost_analysis.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    print(f'  報告已儲存: {report_file}')

    return results


if __name__ == '__main__':
    if '--all' in sys.argv:
        rank_all_etfs()
    elif len(sys.argv) > 1:
        etf_id = sys.argv[1]
        r = analyze_etf_cost(etf_id, monthly_amount=5000, years=5)
        print_cost_report(r)
    else:
        rank_all_etfs()