# -*- coding: utf-8 -*-
"""
Nana Decision Maker - 最終決策模組
===================================
Nana 團隊的最高決策者
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import pandas as pd
from datetime import datetime

class NanaDecisionMaker:
    """
    Nana 的最終決策系統
    
    職責:
    - 接收所有分析資料
    - 做出最終買賣決策
    - 承擔所有責任
    """
    
    def __init__(self):
        self.name = 'Nana'
        self.role = 'Team Leader & Decision Maker'
        self.confidence_threshold = 65
        self.risk_level = 'moderate'
        
        # 決策歷史
        self.decisions = []
    
    def decide(self, symbol, data):
        """
        對單一股票做出決策
        
        參數:
            symbol: 股票代碼
            data: 分析資料 (dict)
        
        返回:
            Decision dict
        """
        score = data.get('Score', 0)
        rsi = data.get('RSI', 50)
        inst_score = data.get('InstScore', 0)
        signal = data.get('Signal', 'WATCH')
        filters = data.get('Filters', [])
        
        # ====== Nana 的決策邏輯 ======
        
        decision = {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'score': score,
            'rsi': rsi,
            'inst_score': inst_score,
            'signal': signal,
            'filters': filters,
            'decision': None,
            'action': None,
            'confidence': 0,
            'reason': [],
            'warning': []
        }
        
        # ====== 負面因素 (否決) ======
        
        if 'RSI_high' in filters:
            decision['warning'].append('RSI過高，不追')
        
        if 'MA_down' in filters:
            decision['warning'].append('趨勢向下，不進')
        
        if 'NoInst' in filters:
            decision['warning'].append('無法人支撐，不進')
        
        if rsi > 80:
            decision['warning'].append('RSI>80，風險過高')
        
        # ====== 決策 ======
        
        # 買進
        if signal == 'BUY' and score >= 65:
            if 'RSI_high' in filters or rsi > 80:
                decision['decision'] = 'HOLD'
                decision['action'] = 'watch'
                decision['confidence'] = 40
                decision['reason'].append('技術面佳但RSI過高，觀望')
            else:
                decision['decision'] = 'BUY'
                decision['action'] = 'buy'
                decision['confidence'] = min(95, score + inst_score / 2)
                decision['reason'].append(f'總分{score}，法人分{inst_score}')
                decision['reason'].append('符合進場標準')
        
        # 觀望
        elif signal == 'buy' or signal == 'WATCH':
            if score >= 60 and inst_score >= 20:
                decision['decision'] = 'CONSIDER'
                decision['action'] = 'consider'
                decision['confidence'] = score * 0.6
                decision['reason'].append('分數接近，可考慮')
            else:
                decision['decision'] = 'WATCH'
                decision['action'] = 'watch'
                decision['confidence'] = 30
                decision['reason'].append('未達進場標準，觀望')
        
        # 不進
        else:
            decision['decision'] = 'NO_ENTRY'
            decision['action'] = 'no_entry'
            decision['confidence'] = 90
            decision['reason'].append('分數過低，不進場')
        
        # ====== 特殊情況 ======
        
        # 法人超強但技術面一般
        if inst_score >= 50 and score < 65:
            if rsi < 70 and 'MA_down' not in filters:
                decision['decision'] = 'MAYBE'
                decision['action'] = 'maybe'
                decision['confidence'] = 45
                decision['reason'].append('法人超強，可觀察')
        
        self.decisions.append(decision)
        return decision
    
    def batch_decide(self, df):
        """
        對多檔股票做出決策
        
        參數:
            df: 分析結果 DataFrame
        
        返回:
            List of decisions
        """
        decisions = []
        
        for _, row in df.iterrows():
            data = row.to_dict()
            symbol = data['Code']
            decision = self.decide(symbol, data)
            decisions.append(decision)
        
        # 按信心度排序
        decisions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return decisions
    
    def get_actionable(self, decisions):
        """取得可執行的決策"""
        actionable = []
        
        for d in decisions:
            if d['action'] in ['buy', 'consider', 'maybe']:
                if d['confidence'] >= 40:
                    actionable.append(d)
        
        return actionable
    
    def print_decisions(self, decisions, top_n=10):
        """格式化輸出決策"""
        print()
        print('='*70)
        print(' Nana 最終決策報告')
        print('='*70)
        print(f' 時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        print()
        
        # 買進決策
        buys = [d for d in decisions if d['decision'] == 'BUY']
        if buys:
            print(f'🔥 買進 ({len(buys)}檔)')
            print('-'*70)
            for d in buys[:top_n]:
                print(f'  {d["symbol"]} | 信心 {d["confidence"]:.0f}% | RSI {d["rsi"]:.1f} | 原因: {d["reason"][0]}')
            print()
        
        # 觀察決策
        considers = [d for d in decisions if d['decision'] in ['CONSIDER', 'MAYBE']]
        if considers:
            print(f'👀 觀察 ({len(considers)}檔)')
            print('-'*70)
            for d in considers[:5]:
                print(f'  {d["symbol"]} | 信心 {d["confidence"]:.0f}% | {d["reason"][0]}')
            print()
        
        # 警告
        warnings = [d for d in decisions if d['warning']]
        if warnings:
            print(f'⚠️ 警告 ({len(warnings)}檔)')
            print('-'*70)
            for d in warnings[:5]:
                print(f'  {d["symbol"]}: {d["warning"][0]}')
            print()
        
        # 不進場
        no_entry = [d for d in decisions if d['decision'] == 'NO_ENTRY']
        print(f'❌ 不進場: {len(no_entry)}檔')
        print()
        
        print('='*70)
        
        # 可執行
        actionable = self.get_actionable(decisions)
        if actionable:
            print()
            print(f'✅ 可執行: {len(actionable)}檔')
            for d in actionable[:5]:
                print(f'  {d["symbol"]} ({d["action"]}) - 信心 {d["confidence"]:.0f}%')
        
        return buys, considers, actionable

def main():
    print('='*50)
    print(' Nana Decision Maker Test')
    print('='*50)
    print()
    
    # 載入分析資料
    try:
        df = pd.read_json('Tina_Quant_System/teams/nana/scan_universe.json')
        print(f'載入 {len(df)} 檔分析資料')
    except:
        print('無分析資料')
        return
    
    # 建立決策者
    nana = NanaDecisionMaker()
    
    # 批量決策
    decisions = nana.batch_decide(df)
    
    # 輸出
    buys, considers, actionable = nana.print_decisions(decisions)
    
    # 儲存
    result = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total': len(decisions),
        'buys': len(buys),
        'considers': len(considers),
        'actionable': len(actionable),
        'decisions': decisions
    }
    
    with open('Tina_Quant_System/teams/nana/nana_decisions.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print()
    print('已儲存: nana_decisions.json')

if __name__ == '__main__':
    main()