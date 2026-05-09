# -*- coding: utf-8 -*-
"""
Ray DCA Scheduler — 自動化排程腳本（長期持有增強版）
功能：
  - 每月1日：自動 DCA 買入（根據推薦組合）
  - 每年1月：年度檢視（重新平衡）
  - 每季：績效報告
  - 自動化觸發：市場崩跌 > 20%、目標達成 > 90%

用法:
  python scripts/dca_scheduler.py weekly      # 每週 review
  python scripts/dca_scheduler.py monthly      # 每月 portfolio 檢視 + DCA 提醒
  python scripts/dca_scheduler.py alert         # 低價警報檢查
  python scripts/dca_scheduler.py annual        # 年度檢視 + 再平衡
  python scripts/dca_scheduler.py quarterly    # 季度績效報告
  python scripts/dca_scheduler.py longterm     # 完整長期持有檢視
  python scripts/dca_scheduler.py dca_reminder  # DCA 買入日提醒（每月1日執行）
"""
import sys
import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

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

# ===== 路徑設定 =====
RAY_DIR = 'C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\ray'
REPORTS_DIR = os.path.join(RAY_DIR, 'reports')
LOG_FILE = os.path.join(REPORTS_DIR, 'dca_analysis_log.json')
PATTERNS_FILE = os.path.join(REPORTS_DIR, 'dca_patterns.json')
LONGTERM_FILE = os.path.join(REPORTS_DIR, 'dca_longterm_log.json')
PORTFOLIO_FILE = os.path.join(REPORTS_DIR, 'dca_portfolio_plan.json')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 預設 DCA ETF（Core 持股）
CORE_ETFS = ['0050', '0056', '00878', '00919', '00713', '00646']
CRASH_THRESHOLD = 20  # 市場崩跌超過此值觸發警報

# Jo 的組合配置
PORTFOLIO_CONFIG = {
    'core': {'etfs': ['0050', '00646'], 'target_pct': 0.70},
    'satellite': {'etfs': ['00878', '00919'], 'target_pct': 0.20},
    'cash': {'etfs': ['00915B'], 'target_pct': 0.10}
}


# ===== 工具函式 =====

def load_analysis_log():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def load_longterm_log():
    try:
        with open(LONGTERM_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'records': [], 'goal_progress': []}


def save_longterm_record(record):
    lt = load_longterm_log()
    lt['records'].append(record)
    lt['records'] = lt['records'][-500:]
    with open(LONGTERM_FILE, 'w', encoding='utf-8') as f:
        json.dump(lt, f, ensure_ascii=False, indent=2)


def get_etf_position(etf_id):
    """抓 ETF 在近1年區間的位置"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        price = close.iloc[-1]
        low = close.min()
        high = close.max()
        return (price - low) / (high - low) * 100 if high > low else 50, float(price)
    except:
        return None, None


def get_twii_change(pdays=30):
    """計算 TWII 近 N 日變化"""
    try:
        twii = yf.Ticker('^TWII').history(period='3mo')['Close']
        if len(twii) < pdays:
            return None
        change = (twii.iloc[-1] / twii.iloc[-pdays] - 1) * 100
        return change
    except:
        return None


def calc_dca_multiplier(position_pct):
    """根據位置計算 DCA 倍數"""
    if position_pct < 30:
        return 2.0, '積極加碼 (2x)'
    elif position_pct < 40:
        return 1.5, '適度加碼 (1.5x)'
    elif position_pct < 60:
        return 1.0, '正常 DCA (1x)'
    elif position_pct < 75:
        return 0.5, '減少一半 (0.5x)'
    else:
        return 0.0, '暫停觀望'


# ===== 每週 Review =====

def weekly_review():
    """每週 DCA Review"""
    print()
    print('=' * 60)
    print(' Ray 每週 DCA Review')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)

    alerts = []
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is None:
            continue

        multiplier, action_label = calc_dca_multiplier(pos)
        alerts.append({'etf_id': etf_id, 'position_pct': round(pos, 1), 'price': price, 'multiplier': multiplier, 'action': action_label})

        pos_indicator = '🟢' if pos < 40 else ('🟡' if pos < 60 else ('⚠️' if pos < 75 else '🔴'))
        print(f'  {pos_indicator} {etf_id} | 位置: {pos:.1f}% | ${price:.2f} | {action_label}')

    # TWII 市場情緒
    print()
    try:
        twii = yf.Ticker('^TWII').history(period='1y')['Close']
        tp = (twii.iloc[-1] - twii.min()) / (twii.max() - twii.min()) * 100
        twii_change = get_twii_change(30)
        print(f'  📊 TWII 位置: {tp:.1f}%', end='')
        if twii_change is not None:
            print(f' | 近30日: {twii_change:+.1f}%')
        else:
            print()
    except:
        pass

    # 檢查市場崩跌
    market_change = get_twii_change(60)
    if market_change and market_change < -CRASH_THRESHOLD:
        print()
        print(f'  🚨【市場崩跌警報】TWII 近60日下跌 {market_change:.1f}%，超過 {CRASH_THRESHOLD}% 門檻')
        print(f'  建議：Ray 核心 ETF 可考慮額外買入')

    print()
    print('=' * 60)
    return alerts


# ===== 每月 DCA 買入提醒 =====

def dca_reminder():
    """
    每月1日自動 DCA 買入提醒
    根據組合配置計算建議金額
    """
    print()
    print('=' * 60)
    print(' 🎯 Ray DCA 每月買入提醒')
    print(f' 日期: {datetime.now().strftime("%Y-%m-%d")}（每月1日）')
    print('=' * 60)
    print()

    # 嘗試讀取組合配置
    portfolio_plan = None
    try:
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            portfolio_plan = json.load(f)
    except:
        pass

    # Jo 的條件
    monthly_budget = portfolio_plan.get('monthly_dca', {}).get('total', 30000) if portfolio_plan else 30000

    print(f'  📅 今日是 DCA 買入日！')
    print(f'  建議月 DCA 預算: NT${monthly_budget:,}')
    print()

    # 各組合建議
    total_dca = 0
    for bucket, config in PORTFOLIO_CONFIG.items():
        bucket_amount = int(monthly_budget * config['target_pct'])
        per_etf = bucket_amount // len(config['etfs']) if config['etfs'] else 0
        total_dca += bucket_amount

        print(f'  【{bucket.upper()} — {config["target_pct"]*100:.0f}%】NT${bucket_amount:,}')
        for etf_id in config['etfs']:
            pos, price = get_etf_position(etf_id)
            if pos is not None:
                mult, action = calc_dca_multiplier(pos)
                adjusted = int(per_etf * mult)
                indicator = '🟢' if mult >= 1.5 else ('🟡' if mult >= 1.0 else ('⚠️' if mult > 0 else '🔴'))
                print(f'    {indicator} {etf_id}: ${price:.2f} (位置{pos:.1f}%) → 建議買 NT${adjusted:,} {action}')
            else:
                print(f'    {etf_id}: 無法取得位置資料')

        print()

    print(f'  💰 本月總建議 DCA: NT${total_dca:,}')
    print()
    print('  ⚠️ 提醒：')
    print('    • 位置 > 75% 的標的建議暫停')
    print('    • 若已超過月預算，選擇核心標的優先')
    print('    • 現金停泊（00915B）可視流動性需求決定')

    # 寫入記錄
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': 'monthly_dca_reminder',
        'budget': monthly_budget,
        'total_dca': total_dca
    }
    save_longterm_record(record)

    print()
    print('=' * 60)
    return record


# ===== 月度 Portfolio 檢視 =====

def monthly_portfolio_review():
    """每月投資組合檢視"""
    print()
    print('=' * 60)
    print(' Ray 每月 Portfolio 檢視')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)

    log = load_analysis_log()
    etf_stats = {}
    for rec in log:
        etf = rec['etf']
        if etf not in etf_stats:
            etf_stats[etf] = {'positions': [], 'actions': []}
        etf_stats[etf]['positions'].append(rec.get('position_pct', 50))
        etf_stats[etf]['actions'].append(rec.get('action', ''))

    print()
    print('【Core ETF DCA 健康檢查】')
    for etf_id in CORE_ETFS:
        stats = etf_stats.get(etf_id, {})
        positions = stats.get('positions', [])
        if not positions:
            print(f'  {etf_id}: 尚無記錄')
            continue
        avg_pos = sum(positions) / len(positions)
        recent_pos = positions[-1]
        action_count = stats.get('actions', [])
        buy_count = sum(1 for a in action_count if '買' in str(a))
        health = '✅ 健康' if avg_pos < 55 else ('⚠️ 注意' if avg_pos < 70 else '❌ 偏高')
        print(f'  {etf_id}:')
        print(f'    平均位置: {avg_pos:.1f}% | 最新位置: {recent_pos:.1f}%')
        print(f'    歷史買進次數: {buy_count}/{len(action_count)}')
        print(f'    建議: {health}')

    print()
    print('【Pattern 學習】')
    analyze_patterns(log)

    print()
    print('【Ray 月度建議】')
    generate_monthly_recommendations(etf_stats)

    print('=' * 60)


def analyze_patterns(log):
    if len(log) < 10:
        print('  記錄不足，暫無 Pattern 分析')
        return
    low_entry = [r for r in log if r.get('position_pct', 100) < 40]
    high_entry = [r for r in log if r.get('position_pct', 0) >= 70]
    print(f'  低價進場 (< 40%): {len(low_entry)} 次')
    print(f'  高價進場 (>= 70%): {len(high_entry)} 次')
    patterns = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'low_entry_count': len(low_entry),
        'high_entry_count': len(high_entry),
        'total_records': len(log)
    }
    try:
        existing = json.load(open(PATTERNS_FILE, 'r', encoding='utf-8'))
    except:
        existing = []
    existing.append(patterns)
    existing = existing[-12:]
    with open(PATTERNS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f'  Pattern 已記錄 (共 {len(existing)} 筆記錄)')


def generate_monthly_recommendations(etf_stats):
    for etf_id in CORE_ETFS:
        stats = etf_stats.get(etf_id, {})
        positions = stats.get('positions', [])
        if not positions:
            continue
        avg_pos = sum(positions) / len(positions)
        if avg_pos < 40:
            rec = '維持或增加 DCA 金額，低價佈局'
        elif avg_pos < 60:
            rec = '維持正常 DCA 金額'
        elif avg_pos < 75:
            rec = '考慮減少 DCA 金額 30-50%'
        else:
            rec = '暫停 DCA，等待價格回落'
        print(f'  {etf_id}: {rec}')


# ===== 低價警報 =====

def alert_low_price():
    """低價警報檢查"""
    print()
    print('=== Ray 低價警報檢查 ===')
    print()
    alerts_found = []
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is None:
            continue
        if pos < 35:
            alerts_found.append({'etf_id': etf_id, 'position_pct': round(pos, 1), 'price': price})
            print(f'  🚨 {etf_id}: 價格位置 {pos:.1f}%（低於35%），DCA 極佳時機')
    if not alerts_found:
        print('  目前無低價警報')
    try:
        shared = TeamShared()
        for a in alerts_found:
            shared.write_alert('DCA_LOW_PRICE', f"Ray: {a['etf_id']} 價格位置 {a['position_pct']}%（低價 DCA 機會）", 'info')
    except:
        pass
    return alerts_found


# ===== 年度檢視 + 再平衡 =====

def annual_review():
    """年度檢視與再平衡"""
    print()
    print('=' * 60)
    print(' 🎆 Ray 年度檢視 + 再平衡')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d")}（每年1月）')
    print('=' * 60)
    print()

    print('【年度再平衡檢查】')
    print('  目標配置:')
    print('    Core 70% (0050, 00646)')
    print('    Satellite 20% (00878, 00919)')
    print('    Cash 10% (00915B)')
    print()
    print('  【各 ETF 現況】')
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is not None:
            mult, action = calc_dca_multiplier(pos)
            print(f'    {etf_id}: ${price:.2f} | 位置 {pos:.1f}% | {action}')
        else:
            print(f'    {etf_id}: 無法取得')

    print()
    print('【再平衡建議】')
    print('  1. 若核心配置偏離 > 5%，優先調整')
    print('  2. 賣出高於目標的部位，買入低於目標的部位')
    print('  3. 高息 ETF (00878, 00919) 配息建議再投入')
    print()
    print('【長期目標檢視】')
    print('  • 距離買房目標: 3-5年')
    print('  • 若 < 2年，應開始降低股票比例（建議股票 < 40%）')
    print('  • 若 > 3年，可維持當前配置')
    print()
    print('【年度學習總結】')
    lt = load_longterm_log()
    records = lt.get('records', [])
    if records:
        low_count = len([r for r in records if r.get('type') == 'low_price_alert'])
        dca_count = len([r for r in records if r.get('type') == 'monthly_dca_reminder'])
        print(f'    過去記錄: 低價警報 {low_count} 次, DCA 提醒 {dca_count} 次')
        if low_count > 5:
            print('    發現: 市場出現多次低價機會，長期學習有效')
    else:
        print('    累積資料不足，等待更多記錄')

    # 寫入年度記錄
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': 'annual_review',
        'action': 'rebalance_check'
    }
    save_longterm_record(record)

    print()
    print('=' * 60)


# ===== 季度績效報告 =====

def quarterly_report():
    """季度績效報告"""
    print()
    print('=' * 60)
    print(' 📊 Ray 季度績效報告')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d")}（每季）')
    print('=' * 60)
    print()

    lt = load_longterm_log()
    records = lt.get('records', [])

    # 分析過去一個季度的數據
    now = datetime.now()
    quarter_start = now - timedelta(days=90)

    quarter_records = [
        r for r in records
        if 'date' in r and datetime.strptime(r['date'], '%Y-%m-%d') >= quarter_start
    ]

    print(f'  【本季度統計】({quarter_start.strftime("%Y-%m-%d")} ~ {now.strftime("%Y-%m-%d")})')
    print(f'    記錄筆數: {len(quarter_records)}')
    print()

    print('  【各 ETF 位置追蹤】')
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is not None:
            mult, action = calc_dca_multiplier(pos)
            trend = '📈' if pos < 50 else ('📊' if pos < 70 else '📉')
            print(f'    {trend} {etf_id}: ${price:.2f} | 位置 {pos:.1f}% | {action}')
        else:
            print(f'    {etf_id}: 無法取得')

    print()
    print('  【 DCA 效果評估】')
    print('    • 若位置持續偏低 → DCA 累積單位數有利')
    print('    • 若位置偏高 → 減少 DCA，等待回調')
    print()
    print('  【下季度建議】')
    avg_positions = {}
    for etf_id in CORE_ETFS:
        pos, _ = get_etf_position(etf_id)
        if pos is not None:
            avg_positions[etf_id] = pos

    if avg_positions:
        avg = sum(avg_positions.values()) / len(avg_positions)
        print(f'    市場平均位置: {avg:.1f}%')
        if avg < 45:
            print('    建議: 市場偏低，可提高 DCA 倍數至 1.5x')
        elif avg < 60:
            print('    建議: 市場正常，维持 1x DCA')
        else:
            print('    建議: 市場偏高，可降低 DCA 倍數至 0.5x')

    # 寫入季度記錄
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': 'quarterly_report',
        'record_count': len(quarter_records)
    }
    save_longterm_record(record)

    print()
    print('=' * 60)


# ===== 長期檢視（每日 Cron 用） =====

def longterm_review():
    """
    Ray DCA 長期檢視（每日執行）
    檢查 DCA 組合狀態，分析市場，若有危機事項則發送推播
    """
    print()
    print('=' * 60)
    print(' 🔍 Ray DCA 長期檢視（每日）')
    print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    print()

    alerts_issued = []
    warnings = []

    # 1. 檢查市場崩跌
    market_change = get_twii_change(60)
    if market_change and market_change < -CRASH_THRESHOLD:
        msg = f'🚨【市場崩跌警報】TWII 近60日下跌 {market_change:.1f}%，超過 {CRASH_THRESHOLD}% 門檻。建議 Ray 核心 ETF 額外買入。'
        warnings.append(msg)
        alerts_issued.append({'level': 'critical', 'message': msg})
        print(f'  {msg}')
    elif market_change and market_change < -10:
        warnings.append(f'⚠️ 市場下跌 {market_change:.1f}%，注意 DCA 倍數')
        print(f'  ⚠️ 市場下跌 {market_change:.1f}%，注意 DCA 倍數')

    # 2. 檢查低價機會
    print()
    print('  【低價警報檢查】')
    low_price_etfs = []
    for etf_id in CORE_ETFS:
        pos, price = get_etf_position(etf_id)
        if pos is not None and pos < 35:
            low_price_etfs.append((etf_id, pos, price))
            mult, action = calc_dca_multiplier(pos)
            print(f'  🚨 {etf_id}: 位置 {pos:.1f}%（低價 DCA！）→ {action}')
        else:
            print(f'  {etf_id}: 位置 {pos:.1f}%' if pos else f'  {etf_id}: 位置 N/A')

    if low_price_etfs:
        msg = f'Ray DCA 低價機會: {", ".join([f"{e}({p:.1f}%)" for e,p,_ in low_price_etfs])}'
        alerts_issued.append({'level': 'info', 'message': msg})

    # 3. TWII 整體位置
    print()
    print('  【市場情緒】')
    try:
        twii = yf.Ticker('^TWII').history(period='1y')['Close']
        tp = (twii.iloc[-1] - twii.min()) / (twii.max() - twii.min()) * 100
        print(f'  TWII 目前位置: {tp:.1f}% (近1年)')

        if tp > 85:
            msg = f'TWII 接近歷史高點（{tp:.1f}%），建議降低 DCA 倍數'
            warnings.append(msg)
            print(f'  ⚠️ {msg}')
        elif tp < 30:
            msg = f'TWII 低點（{tp:.1f}%），建議提高 DCA 倍數'
            warnings.append(msg)
            print(f'  💡 {msg}')
    except:
        print('  無法取得 TWII 資料')

    # 4. 檢查接近目標
    print()
    print('  【目標進度】')
    print('  • 距離買房: 3-5年')
    print('  • 若接近 < 1年，應開始降低股票比例')
    print('  • 若已達成 90%，提醒 Jo')

    # 寫入記錄
    record = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'type': 'daily_longterm_review',
        'market_change_60d': round(market_change, 1) if market_change else None,
        'alerts_issued': len(alerts_issued),
        'warnings': warnings
    }
    save_longterm_record(record)

    # 發送 Alert（若有的話）
    if alerts_issued:
        try:
            shared = TeamShared()
            for alert in alerts_issued:
                shared.write_alert(
                    'DCA_LONGTERM_ALERT' if alert['level'] == 'critical' else 'DCA_INFO',
                    alert['message'],
                    'critical' if alert['level'] == 'critical' else 'info'
                )
        except:
            pass

    print()
    print('=' * 60)
    return alerts_issued


# ===== 主程式 =====

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'weekly'

    modes = {
        'weekly': weekly_review,
        'monthly': monthly_portfolio_review,
        'alert': alert_low_price,
        'annual': annual_review,
        'quarterly': quarterly_report,
        'longterm': longterm_review,
        'dca_reminder': dca_reminder
    }

    if mode in modes:
        modes[mode]()
    else:
        print(f'未知模式: {mode}')
        print('用法: python dca_scheduler.py [weekly|monthly|alert|annual|quarterly|longterm|dca_reminder]')