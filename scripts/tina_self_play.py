"""
Tina 自我博弈系統 (Self-Correction Engine)
當 Tina 決定修正參數時，會先進行內部角色對話
"""

from datetime import datetime

class TinaSelfPlay:
    """內部辯論系統：激進派 vs 保守派"""
    
    def __init__(self):
        self.rounds = 3
        self.decision_log = []
        
    def debate(self, proposed_change):
        """
        執行三輪自我博弈，最終輸出校準後的決策
        """
        print(f"=== Tina 自我博弈開始 ===")
        print(f"原始提案: {proposed_change}")
        print()
        
        # 角色初始化
        radical = {"name": "激進派", "stance": "主張立即修改", "score": 0}
        conservative = {"name": "保守派", "stance": "尋找風險", "score": 0}
        
        # 三輪辯論
        for round_num in range(1, self.rounds + 1):
            print(f"--- 第 {round_num} 輪 ---")
            
            # 激進派發言
            radical_arg = self._radical_argument(proposed_change, round_num)
            print(f"激進派: {radical_arg}")
            radical["score"] += self._score_argument(radical_arg, is_radical=True)
            
            # 保守派反駁
            conservative_arg = self._conservative_argument(proposed_change, round_num)
            print(f"保守派: {conservative_arg}")
            conservative["score"] += self._score_argument(conservative_arg, is_radical=False)
            
            print()
        
        # 裁判決策
        final_decision = self._judge(radical, conservative, proposed_change)
        
        # 記錄
        self._log_decision(proposed_change, radical, conservative, final_decision)
        
        return final_decision
    
    def _radical_argument(self, proposal, round_num):
        """激進派論點"""
        if "RSI" in proposal or "rsi" in proposal:
            if round_num == 1:
                return "目前勝率僅 55%，擴大進場區間能提高交易次數，增加絕對收益。"
            elif round_num == 2:
                return "市場進入多頭，投資人風險胃納提高，應該順勢而為。"
            else:
                return "其他量化系統已採用類似參數，我們落後了。"
        elif "停損" in proposal or "stop" in proposal:
            return "緊縮停損會減少虧損，但也可能被正常波動掃出。"
        return f"立即行動的好處大於等待。落後代價更高。"
    
    def _conservative_argument(self, proposal, round_num):
        """保守派論點"""
        if "RSI" in proposal or "rsi" in proposal:
            if round_num == 1:
                return "擴大區間可能引入過擬合風險，歷史上 RSI 65+ 勝率僅 23%。"
            elif round_num == 2:
                return "多頭市場也可能反轉，我們不知道何時發生。"
            else:
                return "如果這個修改在歷史上導致虧損，現在也不會改變。"
        elif "停損" in proposal or "stop" in proposal:
            return "放寬停損等於放大風險。任何修改都應該經過 100 根 K 線回測。"
        return "Overfitting 是量化系統最大風險，保守估計更安全。"
    
    def _score_argument(self, arg, is_radical):
        """評分論點"""
        score = 5  # 基礎分
        
        # 正面加分
        if any(word in arg for word in ["數據", "回測", "歷史", "證據"]):
            score += 3
        if any(word in arg for word in ["減少虧損", "安全", "穩健"]):
            score += 2
            
        # 負面扣分
        if any(word in arg for word in ["可能", "也許", "不知道"]):
            score -= 2
        if is_radical and any(word in arg for word in ["順勢", "應該", "落後"]):
            score -= 1
            
        return score
    
    def _judge(self, radical, conservative, proposal):
        """裁判整合"""
        print("=== 裁判決策 ===")
        
        # 計算最終分數
        radical_final = radical["score"] / self.rounds
        conservative_final = conservative["score"] / self.rounds
        
        print(f"激進派平均分: {radical_final:.1f}")
        print(f"保守派平均分: {conservative_final:.1f}")
        
        # 決定
        if radical_final > conservative_final + 1:
            # 激進派勝出但要加警告
            decision = f"【有條件通過】{proposal}（注意：保守派提出 {conservative_final:.1f} 分風險）"
            proceed = True
        elif conservative_final > radical_final:
            # 保守派勝出，否決或推遲
            decision = f"【否決/推遲】{proposal}（需更多驗證）"
            proceed = False
        else:
            # 平手，需要更多數據
            decision = f"【待決】{proposal}（建議先進行 100 根 K 線回測）"
            proceed = None
            
        print(f"最終決策: {decision}")
        
        return {
            "decision": decision,
            "proceed": proceed,
            "radical_score": radical_final,
            "conservative_score": conservative_final
        }
    
    def _log_decision(self, proposal, radical, conservative, final):
        """記錄決策"""
        log = f"""
--- Tina 自我博弈記錄 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---
提案: {proposal}
激進派最終分: {final['radical_score']:.1f}
保守派最終分: {final['conservative_score']:.1f}
最終決策: {final['decision']}
"""
        self.decision_log.append(log)


# 使用範例
if __name__ == '__main__':
    engine = TinaSelfPlay()
    
    print("情境：考慮將 RSI 進場上限從 65 調高至 70")
    result = engine.debate("將 RSI 進場上限從 65 調高至 70")
    
    print()
    print("=" * 50)
    print(f"結論: {result['decision']}")
    print(f"是否執行: {result['proceed']}")