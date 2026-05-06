# -*- coding: utf-8 -*-
"""
Ray DCA Longterm Framework — 長期持有適宜性評估
功能：
  - 計算每檔 ETF 的「DCA 適宜性分數」(0-100)
  - 評估維度：穩定性、長期趨勢、配息率、管理費、追蹤準確度
  - 給出長期持有建議

用法:
  python scripts/ray_dca_longterm.py          # 分析所有 Core ETF
  python scripts/ray_dca_longterm.py 0050    # 分析單一 ETF
"""
import yfinance as yf
import pandas as pd
import sys
import os
import json
from datetime import datetime

# Dynamic path setup: project root is parent of 'teams/'
_ScriptDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ScriptDir not in sys.path:
    sys.path.insert(0, _ScriptDir)

try:
    from teams.team_shared import TeamShared
except ModuleNotFoundError:
    _alt = os.path.dirname(_ScriptDir)
    if _alt not in sys.path:
        sys.path.insert(0, _alt)
    import team_shared as _ts
    TeamShared = _ts.TeamShared

sys.stdout.reconfigure(encoding='utf-8')

# ===== 靜態資料 =====

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00881': '國泰台灣5G', '00915': '富邦台灣永續高息',
    '00923': '群益台灣ESG低碳', '00895': '富邦上証', '00762': '元大石油',
    '00915B': '富邦票券利息',
    # ── US ETF（DCA 長線持有）─
    'VTI': 'Vanguard 全美市場', 'VOO': 'Vanguard S&P500',
    'QQQ': 'Invesco QQQ', 'VEA': 'Vanguard 發達市場', 'BND': 'Vanguard 綜合債券',
}

# 管理費（年度%，Source:公開說明書，2024資料）
EXPENSE_RATIOS = {
    '0050': 0.32, '0056': 0.35, '00878': 0.35, '00891': 0.45,
    '00919': 0.42, '00927': 0.68, '00713': 0.40, '00646': 0.56,
    '00662': 0.60, '00757': 0.70, '00881': 0.45, '00915': 0.35,
    '00923': 0.40, '00895': 0.50, '00762': 0.88
}

# 追蹤指數（用於評估追蹤難度）
TRACKING_INDEX = {
    '0050': '台灣50指數', '0056': '台灣高股息指數', '00878': '台灣永續高息指數',
    '00891': '台灣低碳指數', '00919': '台灣精選高息指數', '00927': '統一手創未來指數',
    '00713': '台灣高息低波指數', '00646': 'S&P 500', '00662': 'NASDAQ 100',
    '00757': 'S&P 500等科技巨頭', '00881': '台灣5G指數', '00915': '台灣永續高息',
    '00923': '台灣ESG低碳指數', '00895': '上証指數', '00762': '布蘭特原油'
}

# 歷史年化配息率（%，2020-2024 平均）
DIVIDEND_YIELDS = {
    '0050': 2.0, '0056': 4.5, '00878': 4.8, '00891': 3.2,
    '00919': 5.2, '00927': 4.0, '00713': 5.0, '00646': 1.4,
    '00662': 0.8, '00757': 0.5, '00881': 2.8, '00915': 4.6,
    '00923': 4.2, '00895': 2.5, '00762': 3.5
}

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def get_price_history(etf_id, period='3y'):
    """抓取多年價格歷史"""
    sym = etf_id if etf_id in ('VTI','VOO','QQQ','VEA','BND') else (etf_id + '.TW')
    h = yf.Ticker(sym).history(period=period)
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    return close


def calc_volatility(close):
    """計算年化波動度（%），越低越穩定"""
    returns = close.pct_change().dropna()
    if len(returns) < 60:
        return None
    # 年化：日標準差 × sqrt(252)
    daily_std = returns.std()
    annual_vol = daily_std * (252 ** 0.5) * 100
    return round(annual_vol, 1)


def calc_trend_score(close, years=3):
    """計算長期趨勢分數（0-100）
    - 衡量從歷史低點到現在的累計成長
    - 考慮均線多頭排列程度
    """
    if len(close) < 252:
        return None

    # 3年累計報酬
    cumulative_return = (close.iloc[-1] / close.iloc[0] - 1) * 100

    # 均線排列（多頭：短 > 中 > 長）
    ma12 = close.rolling(252).mean().iloc[-1] if len(close) >= 252 else close.mean()
    ma36 = close.rolling(756).mean().iloc[-1] if len(close) >= 756 else close.mean()
    ma60 = close.rolling(1260).mean().iloc[-1] if len(close) >= 1260 else close.mean()

    # 趨勢分數
    if cumulative_return > 50 and close.iloc[-1] > ma12 > ma36:
        trend_score = 85  # 強多頭
    elif cumulative_return > 30 and close.iloc[-1] > ma12:
        trend_score = 70  # 中多頭
    elif cumulative_return > 0:
        trend_score = 55  # 温和多頭
    elif cumulative_return > -20:
        trend_score = 40  # 偏空
    else:
        trend_score = 25  # 弱勢

    return {
        'cumulative_return': round(cumulative_return, 1),
        'trend_score': trend_score,
        'ma12': round(float(ma12), 2),
        'ma36': round(float(ma36), 2)
    }


def calc_expense_score(etf_id):
    """計算費用分數（0-100），費用越低分數越高"""
    er = EXPENSE_RATIOS.get(etf_id, 0.6)
    if er <= 0.30:
        return 100, er
    elif er <= 0.40:
        return 80, er
    elif er <= 0.50:
        return 65, er
    elif er <= 0.60:
        return 50, er
    elif er <= 0.75:
        return 35, er
    else:
        return 20, er


def calc_dividend_score(etf_id):
    """計算配息分數（0-100）"""
    dy = DIVIDEND_YIELDS.get(etf_id, 2.0)
    if dy >= 5.0:
        return 100, dy
    elif dy >= 4.0:
        return 85, dy
    elif dy >= 3.0:
        return 70, dy
    elif dy >= 2.0:
        return 55, dy
    elif dy >= 1.0:
        return 40, dy
    else:
        return 25, dy


def calc_tracking_score(etf_id, close):
    """計算追蹤準確度分數（0-100）"""
    # 估算追蹤誤差：波動度與大盤的相關性，偏離越小越好
    # 我們用相關係數來近似（相關性高=追蹤好）
    # 若 ETF 有對應的大盤指數（如 0050 對 TWII），比較相關性
    try:
        twii = yf.Ticker('^TWII').history(period='3y')['Close']
        twii = twii[twii.index.isin(close.index)]
        if len(twii) > 60:
            corr = close.corr(twii)
            if corr >= 0.95:
                return 95, round(corr, 3)
            elif corr >= 0.90:
                return 85, round(corr, 3)
            elif corr >= 0.85:
                return 75, round(corr, 3)
            else:
                return 60, round(corr, 3)
    except:
        pass
    return 75, None  # 預設分數


def calc_dca_suitability(etf_id, verbose=True):
    """計算 DCA 適宜性分數（0-100）"""
    name = ETF_NAMES.get(etf_id, etf_id)

    # 1. 穩定性分數（波動度，越低越好）
    close = get_price_history(etf_id, '3y')
    vol = calc_volatility(close)
    if vol is not None:
        if vol <= 12:
            stability_score = 100
        elif vol <= 15:
            stability_score = 85
        elif vol <= 18:
            stability_score = 70
        elif vol <= 22:
            stability_score = 55
        else:
            stability_score = 40
    else:
        stability_score = 50
        vol = 0

    # 2. 長期趨勢分數
    trend_data = calc_trend_score(close)
    trend_score = trend_data['trend_score'] if trend_data else 50

    # 3. 配息率分數
    div_score, div_yield = calc_dividend_score(etf_id)

    # 4. 費用分數
    exp_score, expense_ratio = calc_expense_score(etf_id)

    # 5. 追蹤準確度
    track_score, corr = calc_tracking_score(etf_id, close)

    # 總分（加權平均）
    total_score = round(
        stability_score * 0.30 +
        trend_score * 0.25 +
        div_score * 0.20 +
        exp_score * 0.15 +
        track_score * 0.10, 1
    )

    # 評等
    if total_score >= 80:
        grade = 'A（極推薦 DCA）'
    elif total_score >= 65:
        grade = 'B（推薦 DCA）'
    elif total_score >= 50:
        grade = 'C（普通）'
    elif total_score >= 35:
        grade = 'D（不建議 DCA）'
    else:
        grade = 'F（不適合 DCA）'

    result = {
        'etf_id': etf_id,
        'name': name,
        'total_score': total_score,
        'grade': grade,
        'breakdown': {
            'stability_score': stability_score,
            'volatility_pct': vol,
            'trend_score': trend_score,
            'cumulative_return_3y': trend_data['cumulative_return'] if trend_data else None,
            'dividend_score': div_score,
            'div_yield_pct': div_yield,
            'expense_score': exp_score,
            'expense_ratio_pct': expense_ratio,
            'tracking_score': track_score,
            'corr_with_twii': corr
        },
        'tracking_index': TRACKING_INDEX.get(etf_id, 'N/A')
    }

    if verbose:
        print_result(result)

    return result


def print_result(r):
    name = r['name']
    etf_id = r['etf_id']
    score = r['total_score']
    grade = r['grade']
    b = r['breakdown']

    print()
    print(f'{"="*56}')
    print(f'  DCA 長期持有適宜性評估 — {name} ({etf_id})')
    print(f'{"="*56}')
    print()
    print(f'  📊 總分: {score} / 100  「{grade}」')
    print()
    print(f'  【評估細項】')
    print(f'    ① 價格穩定性:    {b["stability_score"]:>5.0f}/100  (年化波動 {b["volatility_pct"]}%)')
    print(f'    ② 長期趨勢:      {b["trend_score"]:>5.0f}/100  (3年累計 {b["cumulative_return_3y"]}%)')
    print(f'    ③ 配息率:        {b["dividend_score"]:>5.0f}/100  (年化 {b["div_yield_pct"]}%)')
    print(f'    ④ 管理費:        {b["expense_score"]:>5.0f}/100  (年度 {b["expense_ratio_pct"]}%)')
    print(f'    ⑤ 追蹤準確度:    {b["tracking_score"]:>5.0f}/100  (相關係數 {b["corr_with_twii"]})')
    print()
    print(f'  【追蹤指數】{r["tracking_index"]}')
    print()
    print(f'  {'🟢 極推薦 DCA' if score >= 80 else '🟡 推薦 DCA' if score >= 65 else '⚪ 普通' if score >= 50 else '🟠 不建議' if score >= 35 else '🔴 不適合'} — ', end='')
    print(grade)
    print(f'{"="*56}')


def rank_all_core_etfs():
    """對所有核心 DCA ETF 排名"""
    core_etfs = ['0050', '0056', '00878', '00919', '00713', '00646']

    print()
    print('=' * 60)
    print('  Ray DCA 長期持有適宜性排名')
    print(f'  評估時間: {datetime.now().strftime("%Y-%m-%d")}')
    print('=' * 60)

    results = []
    for etf_id in core_etfs:
        try:
            r = calc_dca_suitability(etf_id, verbose=False)
            results.append(r)
        except Exception as e:
            print(f'  {etf_id}: 分析失敗 ({e})')

    results.sort(key=lambda x: x['total_score'], reverse=True)

    print()
    print(f'  {"排名":<4s} {"ETF":<8s} {"名稱":<14s} {"總分":>5s} {"評等":<16s} {"波動":>6s} {"配息":>6s} {"費用":>6s}')
    print(f'  {"-"*4} {"-"*8} {"-"*14} {"-"*5} {"-"*16} {"-"*6} {"-"*6} {"-"*6}')

    for i, r in enumerate(results, 1):
        b = r['breakdown']
        print(f'  {i:<4d} {r["etf_id"]:<8s} {r["name"][:12]:<14s} {r["total_score"]:>5.1f} {r["grade"][:14]:<16s} {b["volatility_pct"]:>5.1f}% {b["div_yield_pct"]:>5.1f}% {b["expense_ratio_pct"]:>5.2f}%')

    print()
    print('  💡 DCA 適宜性說明：')
    print('     • 總分 80+ = 極適合長期 DCA，波動低、配息佳、性價比高')
    print('     • 總分 65-79 = 適合 DCA，核心配置首選')
    print('     • 總分 50-64 = 普通，可作為衛星配置')
    print('     • 總分 < 50 = 不建議 DCA，需謹慎評估')
    print('=' * 60)

    # 儲存結果
    report_file = os.path.join(REPORTS_DIR, 'dca_longterm_suitability.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    print(f'  報告已儲存: {report_file}')

    return results


if __name__ == '__main__':
    etf_ids = sys.argv[1:] if len(sys.argv) > 1 else None

    if etf_ids and len(etf_ids) == 1:
        calc_dca_suitability(etf_ids[0])
    else:
        rank_all_core_etfs()