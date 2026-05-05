# -*- coding: utf-8 -*-
"""
Tina Brain - 邏輯推理引擎 v1.0
================================
五大推理機制：
1. 慢思考推理鏈：強制因果分析
2. 專家委員會：內部多空博弈
3. 案例驅動推理：經驗相關性檢索
4. 壓力測試與假設推演
5. 知識庫邏輯標註
"""
import sqlite3, json, sys, random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DECISION_DB = DATA / "tina_decisions.db"


# ============================================================
# 模組一：慢思考推理鏈（Chain-of-Thought）
# ============================================================
def chain_of_thought(situation: str, indicators: Dict) -> str:
    """
    強制因果分析：每次分析前必須建立完整推理鏈
    """
    tech_bull = indicators.get('tech_bull', '')
    tech_bear = indicators.get('tech_bear', '')
    chip_bull = indicators.get('chip_bull', '')
    chip_bear = indicators.get('chip_bear', '')
    macro = indicators.get('macro', '')
    momentum = indicators.get('momentum', '')

    chain = f"""【慢思考推理鏈 v1.0】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 情境建模
   {situation}

📊 技術面分析
   多方證據：{tech_bull or '無'}
   空方證據：{tech_bear or '無'}

💰 籌碼面分析
   多方證據：{chip_bull or '無'}
   空方證據：{chip_bear or '無'}

🌐 宏觀環境
   {macro or '中性'}

📈 動能評估
   {momentum or '無明顯動能'}

🔎 矛盾點檢索"""
    return chain


def detect_contradictions(rsi: float, macd_hist: float, volume_ratio: float,
                        institutional: str, price_trend: str) -> List[str]:
    """
    矛盾點檢索：主動尋找互斥數據並要求解釋
    """
    contradictions = []

    # 矛盾1：RSI vs 價格趨勢
    if rsi > 65 and price_trend == 'down':
        contradictions.append('⚠️ 矛盾：RSI 過熱但價格趨勢向下 → 可能是主力出貨反彈')

    if rsi < 35 and price_trend == 'up':
        contradictions.append('⚠️ 矛盾：RSI 超賣但價格趨勢向上 → 可能是主力洗盤')

    # 矛盾2：量能 vs 價格變化
    if volume_ratio > 2.0 and price_trend == 'down':
        contradictions.append('⚠️ 矛盾：放量下跌 → 主力可能在派發')

    if volume_ratio < 0.5 and price_trend == 'up':
        contradictions.append('⚠️ 矛盾：縮量上漲 → 動能不足，小心回調')

    # 矛盾3：技術面 vs 籌碼面
    if 'buy' in institutional.lower() and price_trend == 'down':
        contradictions.append('⚠️ 矛盾：法人買超但價格下跌 → 需確認是否為散戶跟單')

    return contradictions


# ============================================================
# 模組二：專家委員會（Multi-Agent）
# ============================================================
class ExpertCommittee:
    """
    模擬三位風格迥異的專家，進行內部辯論
    """
    def __init__(self, symbol: str, indicators: Dict):
        self.symbol = symbol
        self.indicators = indicators

    def trend_seeker(self) -> Dict:
        """趨勢追蹤專家：找突破機會"""
        rsi = self.indicators.get('rsi', 50)
        macd = self.indicators.get('macd_hist', 0)
        price = self.indicators.get('price', 0)
        sma20 = self.indicators.get('sma20', 0)
        sma60 = self.indicators.get('sma60', 0)

        verdict = 'NEUTRAL'
        confidence = 50
        reasoning = []
        action = 'watch'

        if macd > 0 and rsi < 65:
            verdict = 'BULL'
            confidence = 70
            reasoning.append('MACD 多頭排列，趨勢向上')
            action = 'consider_buy'

        if sma20 > sma60 and rsi < 60:
            verdict = 'BULL'
            confidence = max(confidence, 75)
            reasoning.append('MA 多頭黃金交叉確認')

        if rsi < 35 and macd > 0:
            verdict = 'BULL'
            confidence = 80
            reasoning.append('RSI 超賣 + MACD 多頭 → 價值區間進場')

        return {
            'expert': 'TrendSeeker（趨勢派）',
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'action': action
        }

    def risk_monitor(self) -> Dict:
        """風控專家：挖掘崩潰風險"""
        rsi = self.indicators.get('rsi', 50)
        macd = self.indicators.get('macd_hist', 0)
        vol_ratio = self.indicators.get('vol_ratio', 1.0)
        atr = self.indicators.get('atr_pct', 5)
        price = self.indicators.get('price', 0)
        high_52w = self.indicators.get('high_52w', 0)

        verdict = 'NEUTRAL'
        confidence = 50
        reasoning = []
        action = 'watch'
        risks = []

        if rsi > 75:
            verdict = 'BEAR'
            confidence = 80
            reasoning.append('RSI 過熱 >75 → 回調風險高')
            risks.append('RSIOVER')

        if vol_ratio > 3.0:
            verdict = 'BEAR'
            confidence = max(confidence, 75)
            reasoning.append('成交量異常放大 → 主力可能在派發')
            risks.append('VOLSPIKE')

        if price > high_52w * 0.95:
            verdict = 'BEAR'
            confidence = max(confidence, 70)
            reasoning.append('接近 52 週高點 → 上漲空間有限')
            risks.append('ATHRISK')

        if macd < 0 and rsi > 60:
            verdict = 'BEAR'
            confidence = 85
            reasoning.append('MACD 空頭 + RSI 偏高 → 趨勢反轉風險')

        return {
            'expert': 'RiskMonitor（風控派）',
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'action': action,
            'risks': risks
        }

    def quant_analyst(self) -> Dict:
        """量化專家：數學邏輯驗證"""
        rsi = self.indicators.get('rsi', 50)
        macd = self.indicators.get('macd_hist', 0)
        vol_ratio = self.indicators.get('vol_ratio', 1.0)
        sma20 = self.indicators.get('sma20', 0)
        sma60 = self.indicators.get('sma60', 0)
        price = self.indicators.get('price', 0)

        verdict = 'NEUTRAL'
        confidence = 50
        reasoning = []
        action = 'watch'

        # RSI 數學約束
        if 30 < rsi < 45:
            verdict = 'BULL'
            confidence = 75
            reasoning.append('RSI 30-45 復蘇區間 → 數學勝率較高')

        if 45 <= rsi < 55 and macd > 0:
            verdict = 'BULL'
            confidence = 70
            reasoning.append('RSI 中性偏多 + MACD 多頭 → 趨勢確認')

        # 成交量確認
        if vol_ratio > 1.5 and verdict == 'BULL':
            confidence += 10
            reasoning.append('量能放大確認趨勢')

        # MA 排列確認
        if sma20 > sma60:
            confidence += 5
            reasoning.append('MA 多頭排列支持')

        return {
            'expert': 'QuantAnalyst（量化派）',
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'action': action
        }

    def debate(self) -> Tuple[str, str, List[str]]:
        """
        辯證匯總：三方辯論後輸出共識
        返回：(verdict, action, debate_log)
        """
        trend = self.trend_seeker()
        risk = self.risk_monitor()
        quant = self.quant_analyst()

        experts = [trend, risk, quant]

        # 權重：風控30% + 量化35% + 趨勢35%
        weights = {'BULL': 0, 'BEAR': 0, 'NEUTRAL': 0}
        weight_map = {'trend_seeker': 0.35, 'risk_monitor': 0.30, 'quant_analyst': 0.35}

        for exp in experts:
            w = 0.35  # 預設平等
            if exp['expert'] == 'RiskMonitor（風控派）': w = 0.30
            if exp['expert'] == 'QuantAnalyst（量化派）': w = 0.35
            if exp['verdict'] == 'BULL': weights['BULL'] += w * exp['confidence'] / 100
            elif exp['verdict'] == 'BEAR': weights['BEAR'] += w * exp['confidence'] / 100
            else: weights['NEUTRAL'] += w * exp['confidence'] / 100

        # 最終裁決：根據加權分數
        final_score = weights['BULL'] - weights['BEAR']

        debate_log = []
        for exp in experts:
            debate_log.append(f"  {exp['expert']}: {exp['verdict']} ({exp['confidence']}%)")
            if exp['reasoning']:
                for r in exp['reasoning']:
                    debate_log.append(f"    → {r}")

        if final_score > 0.3:
            verdict = 'BULL'
            action = 'consider_buy' if trend['action'] == 'consider_buy' else 'watch'
        elif final_score < -0.3:
            verdict = 'BEAR'
            action = 'avoid' if risk['action'] == 'avoid' else 'watch'
        else:
            verdict = 'NEUTRAL'
            action = 'watch'

        # 風控否決：如果 RiskMonitor 極度看空且信心 > 80%
        if risk['verdict'] == 'BEAR' and risk['confidence'] > 80 and risk['risks']:
            verdict = 'BEAR'
            action = 'avoid'
            debate_log.append(f"\n  🔴 風控否決：{risk['reasoning']}")

        debate_log.append(f"\n  共識裁決：{verdict} | 行動：{action}")

        return verdict, action, debate_log


# ============================================================
# 模組三：案例驅動推理（Experience-Based）
# ============================================================
def find_similar_cases(symbol: str, indicators: Dict, days_back: int = 180) -> List[Dict]:
    """
    從決策資料庫調取相似案例
    """
    try:
        conn = sqlite3.connect(str(DECISION_DB))
        c = conn.cursor()
        c.execute("""SELECT id, ts, symbol, action, decision_text, outcome, pnl_pct, score, reasoning
            FROM decisions WHERE symbol=? ORDER BY ts DESC LIMIT 20""", (symbol,))
        rows = c.fetchall()
        conn.close()

        cases = []
        for row in rows:
            # 簡單相似度計算（基於標的相同）
            cases.append({
                'id': row[0],
                'ts': row[1],
                'symbol': row[2],
                'action': row[3],
                'decision_text': row[4],
                'outcome': row[5],
                'pnl_pct': row[6],
                'score': row[7],
                'reasoning': row[8]
            })
        return cases

    except:
        return []


def case_based_adjustment(symbol: str, indicators: Dict) -> Tuple[str, int, List[str]]:
    """
    案例驅動修正：根據過去相似案例調整決策
    返回：(verdict_modifier, confidence_adjustment, warnings)
    """
    cases = find_similar_cases(symbol, indicators)
    if not cases:
        return 'NEUTRAL', 0, []

    # 找出過去胜率
    resolved_cases = [c for c in cases if c['outcome'] in ('win', 'loss')]
    if not resolved_cases:
        return 'NEUTRAL', 0, []

    wins = sum(1 for c in resolved_cases if c['outcome'] == 'win')
    win_rate = wins / len(resolved_cases)

    warnings = []
    verdict_mod = 'NEUTRAL'
    confidence_adj = 0

    # 失敗模式檢測
    recent_cases = resolved_cases[:5]
    recent_losses = [c for c in recent_cases if c['outcome'] == 'loss']

    if len(recent_losses) >= 3:
        warnings.append(f'⚠️ 警示：{symbol} 近期 {len(recent_losses)} 次失敗記錄，謹慎操作')
        verdict_mod = 'DOWNGRADE'
        confidence_adj = -15

    # 成功模式增強
    recent_wins = [c for c in recent_cases if c['outcome'] == 'win']
    if len(recent_wins) >= 3:
        warnings.append(f'✅ 參考：{symbol} 近期 {len(recent_wins)} 次成功歷史，可適度加倉')
        verdict_mod = 'UPGRADE'
        confidence_adj = 10

    return verdict_mod, confidence_adj, warnings


# ============================================================
# 模組四：壓力測試與假設推演
# ============================================================
def stress_test(entry_price: float, atr_pct: float, position_size: float,
                max_loss_pct: float = -8.0) -> Dict:
    """
    極端情境模擬：市場無預警劇烈反轉時的韌性測試
    """
    # 情境1：當日暴跌 5%
    shock_5 = entry_price * 0.95
    loss_5 = (shock_5 - entry_price) / entry_price * 100
    survived_5 = loss_5 > max_loss_pct

    # 情境2：當日暴跌 8%（觸發停損）
    shock_8 = entry_price * 0.92
    loss_8 = (shock_8 - entry_price) / entry_price * 100
    survived_8 = loss_8 > max_loss_pct

    # 情境3：連續 3 天，每天跌 3%
    three_day = entry_price * (0.97 ** 3)
    loss_3d = (three_day - entry_price) / entry_price * 100
    survived_3d = loss_3d > max_loss_pct

    # 情境4：ATR 2x 烈度波動
    atr_shock = entry_price * (1 - atr_pct * 2 / 100)
    loss_atr = (atr_shock - entry_price) / entry_price * 100
    survived_atr = loss_atr > max_loss_pct

    scenarios = [
        {'name': '單日 -5%', 'loss': round(loss_5, 2), 'survived': survived_5},
        {'name': '單日 -8%', 'loss': round(loss_8, 2), 'survived': survived_8},
        {'name': '連跌 3 天 -3%/天', 'loss': round(loss_3d, 2), 'survived': survived_3d},
        {'name': 'ATR 2x 波動', 'loss': round(loss_atr, 2), 'survived': survived_atr},
    ]

    worst_case = min(scenarios, key=lambda x: x['loss'])
    resilience_score = sum(1 for s in scenarios if s['survived']) / len(scenarios) * 100

    return {
        'scenarios': scenarios,
        'worst_case': worst_case,
        'resilience_score': round(resilience_score, 1),
        'recommended_action': 'reduce_position' if resilience_score < 75 else 'hold'
    }


def dynamic_stop_loss(base_sl: float, atr_pct: float, volatility: str) -> Dict:
    """
    動態停損：根據市場波動度調整保護機制
    """
    if volatility == 'high':
        sl_multiplier = 2.5
        tp_multiplier = 4.0
    elif volatility == 'low':
        sl_multiplier = 1.5
        tp_multiplier = 2.5
    else:
        sl_multiplier = 2.0
        tp_multiplier = 3.0

    return {
        'stop_loss_mult': sl_multiplier,
        'take_profit_mult': tp_multiplier,
        'note': f'Volatility={volatility} -> ATRx{sl_multiplier} stop / ATRx{tp_multiplier} take profit'
    }


# ============================================================
# 模組五：知識庫邏輯標註
# ============================================================
def tag_market_event(volume_ratio: float, price_change: float,
                    rsi_change: float, macd_change: float) -> List[str]:
    """
    將市場資料轉化為邏輯標籤
    """
    tags = []

    # 價量異常標籤
    if volume_ratio > 2.5 and price_change > 3:
        tags.append('VOLUME_SPIKE_PUMP')  # 主力拉抬
    elif volume_ratio > 2.5 and price_change < -3:
        tags.append('VOLUME_SPIKE_DUMP')  # 主力拋售
    elif volume_ratio > 1.5 and price_change > 1:
        tags.append('HEALTHY_BULL')  # 健康多頭
    elif volume_ratio < 0.5 and abs(price_change) < 1:
        tags.append('LOW_VOL_CONSOLIDATION')  # 低量整理

    # RSI 標籤
    if rsi_change > 10 and volume_ratio > 1.5:
        tags.append('RSI_MOMENTUM_BUILT')  # 動能積累
    elif rsi_change < -10 and volume_ratio > 1.5:
        tags.append('RSI_MOMENTUM_BREAK')  # 動能破壞

    # MACD 標籤
    if macd_change > 1.0:
        tags.append('MACD_ACCELERATING')  # MACD 加速
    elif macd_change < -1.0:
        tags.append('MACD_WEAKENING')  # MACD 減速

    return tags


def build_causal_path(symbol: str, tags: List[str],
                     entry_price: float, exit_price: float,
                     outcome: str, holding_days: int) -> Dict:
    """
    建立因果路徑：將訊號與結果掛鉤
    """
    pnl_pct = (exit_price - entry_price) / entry_price * 100 if entry_price > 0 else 0

    causal_path = {
        'symbol': symbol,
        'tags': tags,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': round(pnl_pct, 2),
        'outcome': outcome,
        'holding_days': holding_days,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

    # 因果邏輯推理
    causal_map = {
        'VOLUME_SPIKE_PUMP': {'typical_result': 'win', 'reason': '主力拉抬通常延續'},
        'VOLUME_SPIKE_DUMP': {'typical_result': 'loss', 'reason': '主力出貨後續跌'},
        'RSI_MOMENTUM_BUILT': {'typical_result': 'win', 'reason': '動能積累後延續漲勢'},
        'RSI_MOMENTUM_BREAK': {'typical_result': 'loss', 'reason': '動能破壞趨勢反轉'},
        'LOW_VOL_CONSOLIDATION': {'typical_result': 'breakeven', 'reason': '整理後選擇方向'},
    }

    return causal_path, causal_map


# ============================================================
# 整合：Tina Brain 推理引擎主函數
# ============================================================
def analyze_with_reasoning(symbol: str, indicators: Dict) -> Dict:
    """
    整合五大推理機制，產生完整分析報告
    """
    rsi = indicators.get('rsi', 50)
    macd_hist = indicators.get('macd_hist', 0)
    vol_ratio = indicators.get('vol_ratio', 1.0)
    price = indicators.get('price', 0)
    sma20 = indicators.get('sma20', 0)
    sma60 = indicators.get('sma60', 0)
    atr_pct = indicators.get('atr_pct', 5)
    price_change = indicators.get('price_change', 0)
    rsi_change = indicators.get('rsi_change', 0)
    macd_change = indicators.get('macd_change', 0)
    institutional = indicators.get('institutional', '')
    high_52w = indicators.get('high_52w', price * 1.2)

    # 1. 慢思考推理鏈
    situation = f"{symbol} 現價 ${price}，RSI={rsi}，MACD hist={macd_hist}"
    cot = chain_of_thought(situation, indicators)

    # 2. 矛盾點檢索
    contradictions = detect_contradictions(rsi, macd_hist, vol_ratio, institutional, price_change > 0 and 'up' or 'down')

    # 3. 專家委員會辯論
    committee = ExpertCommittee(symbol, indicators)
    verdict, action, debate_log = committee.debate()

    # 4. 案例驅動修正
    case_mod, case_conf_adj, case_warnings = case_based_adjustment(symbol, indicators)

    # 5. 壓力測試
    stress = stress_test(price, atr_pct, position_size=1.0)
    dynamic_sl = dynamic_stop_loss(price, atr_pct, 'normal')

    # 6. 邏輯標籤
    tags = tag_market_event(vol_ratio, price_change, rsi_change, macd_change)

    # 整合裁決
    final_verdict = verdict
    if case_mod == 'DOWNGRADE':
        final_verdict = 'BEAR'
    elif case_mod == 'UPGRADE':
        final_verdict = 'BULL'

    # 最終行動建議
    if final_verdict == 'BULL' and action == 'consider_buy':
        recommended_action = f"進場：停損 ATR×{dynamic_sl['stop_loss_mult']}，目標 ATR×{dynamic_sl['take_profit_mult']}"
    elif final_verdict == 'BEAR' or action == 'avoid':
        recommended_action = "觀望：市場情緒過熱或存在結構性風險"
    else:
        recommended_action = "等待：等待明確進場訊號"

    report = {
        'symbol': symbol,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'indicators': indicators,
        'verdict': final_verdict,
        'action': recommended_action,
        'chain_of_thought': cot,
        'contradictions': contradictions,
        'expert_debate': debate_log,
        'case_warnings': case_warnings,
        'stress_test': stress,
        'logical_tags': tags,
        'resilience_score': stress['resilience_score'],
    }

    return report


def print_report(report: Dict):
    """格式化輸出分析報告"""
    print("="*70)
    print(f"  Tina Brain 推理報告 - {report['symbol']}")
    print(f"  {report['timestamp']}")
    print("="*70)

    print(f"\n【裁決】{report['verdict']}")
    print(f"【行動】{report['action']}")

    print(f"\n【邏輯標籤】{', '.join(report['logical_tags']) if report['logical_tags'] else '無'}")

    if report['contradictions']:
        print(f"\n【矛盾點檢索】")
        for c in report['contradictions']:
            print(f"  {c}")

    print(f"\n【專家辯論】")
    for line in report['expert_debate']:
        print(line)

    if report['case_warnings']:
        print(f"\n【案例警示】")
        for w in report['case_warnings']:
            print(f"  {w}")

    print(f"\n【壓力測試】")
    for s in report['stress_test']['scenarios']:
        status = '✅' if s['survived'] else '❌'
        print(f"  {status} {s['name']}: 損失 {s['loss']}%")
    print(f"  韌性分數：{report['resilience_score']}%")

    print("="*70)


# ============================================================
# 主程式：測試
# ============================================================
if __name__ == '__main__':
    # 測試範例：2359.TW
    sample_indicators = {
        'rsi': 56.9,
        'macd_hist': 0.76,
        'vol_ratio': 3.9,
        'price': 119,
        'sma20': 114,
        'sma60': 117,
        'atr_pct': 5.1,
        'price_change': 8.7,
        'rsi_change': 0,
        'macd_change': 0,
        'institutional': '中立',
        'high_52w': 176,
    }

    report = analyze_with_reasoning('2359.TW', sample_indicators)
    print_report(report)