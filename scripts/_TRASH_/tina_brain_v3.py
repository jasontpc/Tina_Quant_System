"""
Tina Brain - Thinking Module v3
具備慢思考、反思機制、專家委員會的智能大腦
"""

from datetime import datetime
import json
import os

class TinaBrain:
    """Tina 的智能大腦核心"""
    
    def __init__(self):
        self.config_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\configs\tina_brain_config_v3.json'
        self.knowledge_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tina_knowledge.db'
        self.reports_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports'
        self.memory_path = r'C:\Users\USER\.openclaw\workspace\memory'
        
    def think(self, objective, context=None):
        """
        慢思考機制 - Chain-of-Thought
        在執行任何動作前，先進行完整思考
        """
        thought_log = []
        
        # Step 1: 目標確認
        thought_log.append(f"【目標確認】{objective}")
        
        # Step 2: 資訊收集
        known = context if context else {}
        missing = self._identify_missing_info(objective, known)
        thought_log.append(f"【資訊收集】已知: {list(known.keys()) if known else '無'} | 缺口: {missing}")
        
        # Step 3: 假設形成
        hypotheses = self._form_hypotheses(objective, known)
        thought_log.append(f"【假設形成】{hypotheses}")
        
        # Step 4: 風險評估
        risks, backups = self._assess_risks(objective, known)
        thought_log.append(f"【風險評估】風險: {risks} | 備案: {backups}")
        
        # Step 5: 執行計劃
        plan = self._create_execution_plan(objective, known, hypotheses)
        thought_log.append(f"【執行計劃】{plan}")
        
        return {
            'status': 'thought_complete',
            'thought_log': thought_log,
            'plan': plan,
            'confidence': self._calculate_confidence(known, risks),
            'requires_committee': len(risks) > 2 or '核心架構' in objective
        }
    
    def _identify_missing_info(self, objective, known):
        """辨識缺少的資訊"""
        missing = []
        if '分析' in objective or '建議' in objective:
            if 'market_data' not in known:
                missing.append('市場數據')
            if 'recent_trades' not in known:
                missing.append('近期交易')
        return missing
    
    def _form_hypotheses(self, objective, known):
        """形成假設路徑"""
        return f"可能路徑: (1) 直接執行 (2) 收集更多資料 (3) 召開專家委員會"
    
    def _assess_risks(self, objective, known):
        """風險評估"""
        risks = []
        backups = []
        
        if '修改' in objective or '調整' in objective:
            risks.append('可能影響現有策略穩定性')
            backups.append('先在測試環境驗證')
            
        if '交易' in objective:
            risks.append('市場波動可能導致虧損')
            backups.append('設定嚴格停損')
            
        return risks, backups
    
    def _create_execution_plan(self, objective, known, hypotheses):
        """建立執行計劃"""
        return "步驟: (1) 收集必要資訊 (2) 進行自我反思 (3) 必要時召開委員會 (4) 執行並記錄"
    
    def _calculate_confidence(self, known, risks):
        """計算信心度"""
        base = 0.8
        if len(risks) > 2:
            base -= 0.2
        if not known:
            base -= 0.3
        return max(0.3, min(0.95, base))
    
    def self_reflect(self, decision, outcome=None):
        """
        自我反思三層機制
        Layer 1: 提議 | Layer 2: 批判 | Layer 3: 決策
        """
        reflection = {
            'layer_1_proposal': self._layer_1_propose(decision),
            'layer_2_critique': self._layer_2_critique(decision),
            'layer_3_decision': self._layer_3_decide(decision),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 記錄反思日誌
        self._save_reflection_log(reflection)
        
        return reflection
    
    def _layer_1_propose(self, decision):
        """第一層：策略師提議"""
        return {
            'role': '策略師',
            'suggestion': f'建議: {decision.get(\"action\", \"繼續監控\")}',
            'reasoning': '根據目前數據，這是最優方案'
        }
    
    def _layer_2_critique(self, decision):
        """第二層：黑粉/審核員批判"""
        critiques = []
        
        # 扮演反對者找漏洞
        if decision.get('action') == 'buy':
            critiques.append('可能買在高點，需確認 RSI 是否過熱')
        if decision.get('confidence', 1) < 0.7:
            critiques.append('信心度不足，可能有未預見風險')
        if '修改' in decision.get('action', ''):
            critiques.append('直接修改可能影響生產環境穩定性')
            
        return {
            'role': '黑粉/審核員',
            'critiques': critiques if critiques else ['目前看不出明顯漏洞'],
            'verdict': '可以執行（带警示）' if critiques else '建議執行'
        }
    
    def _layer_3_decide(self, decision):
        """第三層：裁判決策"""
        layer1 = self._layer_1_propose(decision)
        layer2 = self._layer_2_critique(decision)
        
        if layer2['critiques']:
            final_action = f"{layer1['suggestion']}（注意: {', '.join(layer2['critiques'][:2])}）"
        else:
            final_action = layer1['suggestion']
            
        return {
            'role': '裁判',
            'final_decision': final_action,
            'confidence': decision.get('confidence', 0.7),
            'proceed': len(layer2['critiques']) <= 2
        }
    
    def expert_committee(self, decision_topic):
        """
        專家委員會 - 複雜決策時模擬三位專家
        """
        committee = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'topic': decision_topic,
            'members': []
        }
        
        # 專家 1: 量化分析師 (35%)
        qa = {
            'role': '量化分析師',
            'view': self._quant_analyst_view(decision_topic),
            'weight': 0.35
        }
        committee['members'].append(qa)
        
        # 專家 2: 資深開發者 (35%)
        dev = {
            'role': '資深開發者',
            'view': self._senior_dev_view(decision_topic),
            'weight': 0.35
        }
        committee['members'].append(dev)
        
        # 專家 3: 風控長 (30%)
        risk = {
            'role': '風控長',
            'view': self._risk_officer_view(decision_topic),
            'weight': 0.30
        }
        committee['members'].append(risk)
        
        # 計算加權共識
        committee['consensus'] = self._calculate_consensus(committee['members'])
        
        # 記錄決策
        self._save_committee_decision(committee)
        
        return committee
    
    def _quant_analyst_view(self, topic):
        """量化分析師觀點"""
        if '修改' in topic or '調整' in topic:
            return '需有足夠回測數據支持，勝率需 >55%，獲利因子 >1.1'
        elif '進場' in topic or '買入' in topic:
            return '檢查 RSI、MA、動量三維度信號一致性'
        else:
            return '需要更多量化數據支援決策'
    
    def _senior_dev_view(self, topic):
        """資深開發者觀點"""
        if '修改' in topic or '調整' in topic:
            return '禁止直接修改 main.py，新建策略檔案如 tina_v{N}_auto_patch.py'
        elif '自動' in topic:
            return '需確保有 safety rails，防止無限交易'
        else:
            return '系統架構穩定，風險可控'
    
    def _risk_officer_view(self, topic):
        """風控長觀點"""
        if '進場' in topic or '買入' in topic:
            return '單筆虧損不得超過 -8%，總部位不超過 40%'
        elif '修改' in topic:
            return '修改需經過回測驗證，並保留舊版'
        else:
            return '資金安全優先於獲利'
    
    def _calculate_consensus(self, members):
        """計算加權共識"""
        return {
            'recommendation': '執行，但需遵守風控限制',
            'agreements': ['量化支持修改', '開發確認可控', '風控設定上限'],
            'disagreements': [],
            'final_weight': sum(m['weight'] for m in members)
        }
    
    def _save_reflection_log(self, reflection):
        """儲存反思日誌"""
        log_path = os.path.join(self.reports_path, f'tina_self_reflection_log.md')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n## 反思記錄 {reflection['timestamp']}\n")
            f.write(f"**提議**: {reflection['layer_1_proposal']['suggestion']}\n")
            f.write(f"**批判**: {reflection['layer_2_critique']['critiques']}\n")
            f.write(f"**決策**: {reflection['layer_3_decision']['final_decision']}\n")
    
    def _save_committee_decision(self, committee):
        """儲存委員會決策"""
        log_path = os.path.join(self.reports_path, f'tina_committee_decisions.md')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n## 專家委員會決策 {committee['timestamp']}\n")
            f.write(f"**主題**: {committee['topic']}\n")
            for m in committee['members']:
                f.write(f"- {m['role']}: {m['view']}\n")
            f.write(f"**共識**: {committee['consensus']['recommendation']}\n")
    
    def save_to_memory(self, insight, category):
        """更新長期記憶"""
        memory_file = os.path.join(self.memory_path, 'long_term_memory.json')
        
        # 讀取現有記憶
        existing = []
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        # 添加新洞察
        existing.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'category': category,
            'insight': insight,
            'source': 'TinaBrain v3'
        })
        
        # 只保留最近 100 條
        existing = existing[-100:]
        
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    # 測試 Tina 大腦
    brain = TinaBrain()
    
    # 測試慢思考
    result = brain.think('分析 2382 廣達是否應該進場', {'price': 312.5, 'rsi': 44.9})
    print("=== 慢思考結果 ===")
    for step in result['thought_log']:
        print(step)
    print(f"信心度: {result['confidence']}")
    print(f"需要委員會: {result['requires_committee']}")
    
    # 測試自我反思
    print("\n=== 自我反思 ===")
    decision = {'action': 'buy 2382', 'confidence': 0.75}
    reflection = brain.self_reflect(decision)
    print(f"最終決策: {reflection['layer_3_decision']['final_decision']}")