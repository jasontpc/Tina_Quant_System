# -*- coding: utf-8 -*-
"""
Ray Learner — 自主學習模組
功能：分析過往模擬交易表現，根據結果調整 DCA 參數，自動學習並優化策略
"""
import yfinance as yf
import pandas as pd
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
TRADES_FILE = BASE_DIR / 'autonomous_trades.json'
RECOMMENDATIONS_FILE = BASE_DIR / 'ray_recommendations.json'
RAY_ETF_DCA_FILE = BASE_DIR / 'ray_etf_dca.py'
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\memory\Ray_learnings.md')


def load_trades():
    """載入交易記錄"""
    if not TRADES_FILE.exists():
        return None
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def load_recommendations():
    """載入既有建議"""
    if not RECOMMENDATIONS_FILE.exists():
        return {'recommendations': [], 'learning_history': []}
    try:
        with open(RECOMMENDATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'recommendations': [], 'learning_history': []}


def save_recommendations(data):
    """儲存建議"""
    with open(RECOMMENDATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def analyze_trades_performance(trades_data):
    """分析交易表現（原有功能）"""
    trades = trades_data.get('trades', [])
    if not trades:
        return None
    
    # 依 ETF 分組
    etf_groups = {}
    for t in trades:
        eid = t['etf_id']
        if eid not in etf_groups:
            etf_groups[eid] = []
        etf_groups[eid].append(t)
    
    learnings = []
    
    for etf_id, etf_trades in etf_groups.items():
        # 計算各 position 的表現
        position_results = {}
        for t in etf_trades:
            if t.get('action', '').startswith('DCA'):
                pos = t.get('position_pct', 50)
                bucket = int(pos / 10) * 10  # 每10%一組
                if bucket not in position_results:
                    position_results[bucket] = {'trades': 0, 'total_return': 0}
                position_results[bucket]['trades'] += 1
        
        # 找出最佳進場位置
        best_position = None
        if position_results:
            best_position = max(position_results.keys(), key=lambda k: position_results[k]['trades'])
        
        learnings.append({
            'etf_id': etf_id,
            'name': etf_trades[0].get('name', etf_id),
            'best_entry_position': best_position,
            'position_samples': position_results
        })
    
    return learnings


def analyze_longterm_learning():
    """
    長期學習維度（新增功能）
    1. 過去1個月：市場情緒、成本變化
    2. 過去3個月：ETF 表現、相對強度
    3. 過去1年：整體組合報酬、DCA 效果
    4. 過去5年：長期趨勢、通貨膨脹調整
    """
    print()
    print('【長期學習分析】')
    
    # 嘗試讀取長期記錄
    LONGTERM_FILE = BASE_DIR.parent / 'reports' / 'dca_longterm_log.json'
    try:
        with open(LONGTERM_FILE, 'r', encoding='utf-8') as f:
            lt_data = json.load(f)
    except:
        lt_data = {'records': []}
    
    records = lt_data.get('records', [])
    now = datetime.now()
    
    # 時間分層分析
    analysis = {}
    
    # 1. 近1月
    month_ago = now - timedelta(days=30)
    recent_records = [r for r in records if 'date' in r and datetime.strptime(r['date'].split()[0], '%Y-%m-%d') >= month_ago]
    analysis['last_1month'] = {
        'count': len(recent_records),
        'types': list(set([r.get('type', 'unknown') for r in recent_records]))
    }
    print(f'  近1月記錄: {len(recent_records)} 筆')
    
    # 2. 近3月
    quarter_ago = now - timedelta(days=90)
    quarter_records = [r for r in records if 'date' in r and datetime.strptime(r['date'].split()[0], '%Y-%m-%d') >= quarter_ago]
    analysis['last_3months'] = {
        'count': len(quarter_records)
    }
    print(f'  近3月記錄: {len(quarter_records)} 筆')
    
    # 3. 近1年
    year_ago = now - timedelta(days=365)
    year_records = [r for r in records if 'date' in r and datetime.strptime(r['date'].split()[0], '%Y-%m-%d') >= year_ago]
    analysis['last_1year'] = {
        'count': len(year_records)
    }
    print(f'  近1年記錄: {len(year_records)} 筆')
    
    # 4. DCA 效果評估
    dca_reminders = [r for r in records if r.get('type') == 'monthly_dca_reminder']
    low_price_alerts = [r for r in records if r.get('type') == 'low_price_alert' or (r.get('position_pct', 100) < 35)]
    
    print()
    print(f'  【DCA 累積效果】')
    print(f'    DCA 提醒次數: {len(dca_reminders)}')
    print(f'    低價警報次數: {len(low_price_alerts)}')
    
    # 5. 長期趨勢觀察
    if len(year_records) >= 3:
        market_positions = [r.get('market_change_60d') for r in year_records if r.get('market_change_60d') is not None]
        if market_positions:
            avg_change = sum(market_positions) / len(market_positions)
            print(f'    平均市場變化: {avg_change:+.1f}%')
    
    return analysis


def calc_longterm_adjustments(analysis):
    """
    根據長期學習輸出調整建議
    """
    recommendations = []
    
    # DCA 金額調整建議
    dca_count = analysis.get('last_3months', {}).get('count', 0)
    if dca_count >= 10:
        # 有足夠數據，建議調整
        recommendations.append({
            'type': 'dca_amount_adjustment',
            'suggestion': '維持當前 DCA 金額',
            'reason': f'過去3個月有 {dca_count} 筆記錄，策略穩定'
        })
    elif dca_count < 3:
        recommendations.append({
            'type': 'dca_amount_adjustment',
            'suggestion': '增加 DCA 頻率或金額',
            'reason': 'DCA 記錄不足，需加強累積'
        })
    
    return recommendations


def evaluate_goal_progress():
    """
    評估長期目標達成進度
    Jo 的目標：3-5年內買房頭期款
    """
    print()
    print('【長期目標進度評估】')
    
    # 讀取組合資料
    PORTFOLIO_FILE = BASE_DIR.parent / 'reports' / 'dca_portfolio_plan.json'
    try:
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            portfolio = json.load(f)
    except:
        portfolio = {}
    
    goal_years = portfolio.get('goal_years', 4)
    jo_capital = portfolio.get('jo_capital', 2500000)
    
    print(f'  目標: {goal_years}年內買房頭期款')
    print(f'  預算: NT${jo_capital:,}')
    print(f'  距離目標: 3-5年（中位數 {goal_years} 年）')
    print()
    print(f'  💡 若接近 < 1年，應開始降低股票比例至 40%')
    print(f'  💡 若 > 3年，可維持當前 DCA 配置')
    print(f'  💡 若市場低點，可考慮提高核心配置')
    
    return {
        'goal_years': goal_years,
        'target_capital': jo_capital,
        'current_progress': '追蹤中'
    }


def generate_recommendations(learnings, trades_data):
    """根據分析生成調整建議"""
    now = datetime.now()
    summary = trades_data.get('summary', {})
    trades = trades_data.get('trades', [])
    
    recommendations = []
    
    # 分析最佳 DCA 位置（只看有真實報酬的樣本）
    entry_positions = {}
    for l in learnings:
        if l['best_entry_position'] is not None:
            # 檢查該 ETF 是否有實質交易回報（有 exit_price 或 total_return > 0）
            etf_id = l['etf_id']
            etf_trades = [t for t in trades if t.get('etf_id') == etf_id]
            has_real_return = any(
                t.get('exit_price') is not None or t.get('total_return', 0) != 0
                for t in etf_trades
            )
            if not has_real_return and len(etf_trades) < 5:
                continue  # 跳過無真實報酬且交易次數少於5筆的 ETF
            
            bp = l['best_entry_position']
            if bp not in entry_positions:
                entry_positions[bp] = 0
            entry_positions[bp] += 1
    
    # 最常勝出的進場位置
    if entry_positions:
        best_overall_position = max(entry_positions.keys(), key=lambda k: entry_positions[k])
        recommendations.append({
            'type': 'entry_threshold',
            'current': 60,
            'suggested': best_overall_position,
            'reason': f'歷史表現顯示位置 {best_overall_position}% 以下進場勝率最高',
            'confidence': entry_positions[best_overall_position] / max(sum(entry_positions.values()), 1)
        })
    
    # 根據 summary 分析報酬（過濾 total_return=0 的 ETF）
    valid_summary = {
        k: v for k, v in summary.items()
        if v.get('total_return_pct', 0) != 0 or v.get('total_trades', 0) >= 5
    }
    
    top_performers = []
    bottom_performers = []
    if valid_summary:
        sorted_summary = sorted(valid_summary.items(), key=lambda x: x[1].get('total_return_pct', 0), reverse=True)
        top_performers = [x[0] for x in sorted_summary[:3] if x[1].get('total_return_pct', 0) > 0]
        bottom_performers = [x[0] for x in sorted_summary[-2:] if x[1].get('total_return_pct', 0) < 0]
    
    # 防止 top_etfs 和 reduce_etfs 衝突（00917 同時上榜的問題）
    if top_performers and bottom_performers:
        conflict = set(top_performers) & set(bottom_performers)
        if conflict:
            # 衝突的 ETF 移出 bottom，保留在 top（報酬為正）
            bottom_performers = [e for e in bottom_performers if e not in conflict]
    
    if top_performers:
        recommendations.append({
            'type': 'top_etfs',
            'etfs': top_performers,
            'reason': '這些 ETF 在模擬中表現最好，建議提高 DCA 權重'
        })
    
    if bottom_performers:
        recommendations.append({
            'type': 'reduce_etfs',
            'etfs': bottom_performers,
            'reason': '這些 ETF 在模擬中表現較差，建議減少 DCA 金額'
        })
    
    return recommendations


def update_ray_etf_dca(recommendations):
    """自動更新 ray_etf_dca.py 的參數"""
    entry_threshold = 60
    for rec in recommendations:
        if rec['type'] == 'entry_threshold':
            entry_threshold = rec['suggested']
            break
    
    # 讀取當前內容
    if not RAY_ETF_DCA_FILE.exists():
        return False
    
    with open(RAY_ETF_DCA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替換門檻參數
    old_patterns = ['position_pct < 60', 'position_pct < 40', 'position_pct < 70']
    for old in old_patterns:
        if old in content:
            content = content.replace(old, old.replace('60', str(entry_threshold)))
            content = content.replace(old.replace('60', '40'), f'position_pct < {max(entry_threshold - 20, 30)}')
            content = content.replace(old.replace('60', '70'), f'position_pct < {min(entry_threshold + 10, 80)}')
            break
    
    with open(RAY_ETF_DCA_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def save_learnings_to_memory(learnings, recommendations, trades_data):
    """記錄學習結果到 memory/Ray_learnings.md"""
    now = datetime.now()
    summary = trades_data.get('summary', {})
    
    content = f"""# Ray 自主學習記錄 — {now.strftime('%Y-%m-%d')}

## 學習時間
{now.isoformat()}

## 學習數據來源
- 模擬交易筆數: {len(trades_data.get('trades', []))}
- 分析 ETF 數: {len(learnings)}

## 學習結果

### 最佳進場位置分析
"""
    for l in learnings:
        content += f"\n#### {l['name']} ({l['etf_id']})\n"
        content += f"- 最佳進場位置: {l['best_entry_position']}%\n"
        content += f"- 位置樣本: {l['position_samples']}\n"
    
    content += "\n## 調整建議\n"
    for rec in recommendations:
        content += f"- **{rec['type']}**: {rec.get('reason', '')}\n"
    
    content += f"\n## 組合表現摘要\n"
    if summary:
        for etf_id, s in summary.items():
            content += f"- {etf_id}: 成本 ${s['total_cost']:,.0f} | 報酬 {s['total_return_pct']:+.1f}%\n"
    else:
        content += "- 無足夠數據\n"
    
    content += f"\n---\n"
    
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()
        content = existing + '\n' + content
    else:
        content = '# Ray 自主學習記錄\n\n' + content
    
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'學習記錄已寫入 {MEMORY_FILE}')


def run_learner():
    """主執行流程"""
    print('=== Ray 自主學習系統（增強版）===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    
    # 1. 長期學習分析（新增）
    print('[Step 1] 長期學習分析...')
    lt_analysis = analyze_longterm_learning()
    print()
    
    # 2. 目標進度評估
    print('[Step 2] 長期目標進度...')
    goal_progress = evaluate_goal_progress()
    print()
    
    # 3. 長期調整建議
    lt_recommendations = calc_longterm_adjustments(lt_analysis)
    print('[Step 3] 長期調整建議...')
    for rec in lt_recommendations:
        print(f'  • {rec["type"]}: {rec.get("suggestion", "")} — {rec.get("reason", "")}')
    print()
    
    # 4. 載入交易記錄（原有功能）
    print('[Step 4] 載入交易記錄...')
    trades_data = load_trades()
    if not trades_data:
        print('  [警告] 無交易記錄，將僅執行長期學習')
        print()
    else:
        print(f'  交易筆數: {len(trades_data.get("trades", []))}')
        print()
        
        # 5. 分析表現
        print('[Step 5] 分析交易表現...')
        learnings = analyze_trades_performance(trades_data)
        if not learnings:
            print('  [警告] 分析失敗')
        else:
            for l in learnings:
                print(f'  {l["name"]}: 最佳進場位置 {l["best_entry_position"]}%')
        print()
        
        # 6. 生成建議
        print('[Step 6] 生成調整建議...')
        recommendations = generate_recommendations(learnings, trades_data)
        print(f'  生成 {len(recommendations)} 項建議')
        for rec in recommendations:
            print(f'  • {rec["type"]}: {rec.get("reason", "")}')
        print()
        
        # 7. 儲存建議
        rec_data = load_recommendations()
        rec_data['recommendations'] = recommendations + lt_recommendations
        rec_data['learning_history'].append({
            'timestamp': datetime.now().isoformat(),
            'learnings': learnings,
            'recommendations': recommendations,
            'longterm_analysis': lt_analysis,
            'goal_progress': goal_progress
        })
        save_recommendations(rec_data)
        print(f'  已儲存到 {RECOMMENDATIONS_FILE}')
        print()
        
        # 8. 更新 ray_etf_dca.py
        print('[Step 7] 更新 DCA 參數...')
        updated = update_ray_etf_dca(recommendations)
        if updated:
            print('  ✓ 已更新 ray_etf_dca.py')
        else:
            print('  ✗ 更新失敗')
        print()
        
        # 9. 寫入 memory
        print('[Step 8] 記錄學習結果...')
        save_learnings_to_memory(learnings, recommendations, trades_data)
    
    # 10. 寫入長期學習記錄
    print('[Step 9] 更新長期學習記錄...')
    LONGTERM_LEARNING_FILE = BASE_DIR.parent / 'reports' / 'dca_longterm_learning.json'
    try:
        existing = json.load(open(LONGTERM_LEARNING_FILE, 'r', encoding='utf-8'))
    except:
        existing = {'history': []}
    
    existing['history'].append({
        'timestamp': datetime.now().isoformat(),
        'longterm_analysis': lt_analysis,
        'goal_progress': goal_progress,
        'recommendations': lt_recommendations
    })
    existing['history'] = existing['history'][-100:]
    
    with open(LONGTERM_LEARNING_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f'  已寫入長期學習記錄')
    
    print()
    print('=== 學習完成（長期視角已加入）===')
    return rec_data if 'rec_data' in dir() else None


if __name__ == '__main__':
    run_learner()
