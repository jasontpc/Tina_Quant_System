"""
Tina 大腦 - 個股策略載入器
根據股票代碼自動載入對應的個股策略配置
"""

import json
import os

class StockStrategyLoader:
    """個股策略載入器"""
    
    def __init__(self):
        self.strategies_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\configs\stock_strategies'
        self.cache = {}  # 簡單快取
        
    def load_strategy(self, stock_code):
        """
        載入指定股票的策略配置
        """
        # 檢查快取
        if stock_code in self.cache:
            return self.cache[stock_code]
        
        # 嘗試多個副檔名
        for ext in ['.json']:
            path = os.path.join(self.strategies_dir, f'{stock_code}{ext}')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.cache[stock_code] = config
                    return config
        
        return None
    
    def get_stock_character(self, stock_code):
        """取得個股特徵描述"""
        config = self.load_strategy(stock_code)
        if config and 'stock_character' in config:
            return config['stock_character']
        return {'label': 'unknown', 'bias': 'unknown'}
    
    def get_brain_instructions(self, stock_code):
        """取得大腦思考指令"""
        config = self.load_strategy(stock_code)
        if config and 'brain_instructions' in config:
            return config['brain_instructions']
        return {}
    
    def get_entry_params(self, stock_code):
        """取得進場參數"""
        config = self.load_strategy(stock_code)
        if config and 'entry' in config:
            return config['entry']
        return {}
    
    def get_exit_params(self, stock_code):
        """取得出場參數"""
        config = self.load_strategy(stock_code)
        if config and 'exit' in config:
            return config['exit']
        return {}
    
    def get_volatility_tier(self, stock_code):
        """取得波動性等級"""
        config = self.load_strategy(stock_code)
        if config and 'volatility_tier' in config:
            return config['volatility_tier']
        return 'medium'
    
    def get_atr_multiplier(self, stock_code):
        """取得 ATR 倍數"""
        config = self.load_strategy(stock_code)
        if config and 'stock_character' in config:
            return config['stock_character'].get('atr_multiplier', 1.0)
        return 1.0
    
    def list_all_stocks(self):
        """列出所有已配置的股票"""
        stocks = []
        for f in os.listdir(self.strategies_dir):
            if f.endswith('.json'):
                stock_code = f.replace('.json', '')
                config = self.load_strategy(stock_code)
                if config:
                    stocks.append({
                        'code': stock_code,
                        'name': config.get('name', 'unknown'),
                        'market': config.get('market', 'unknown'),
                        'type': config.get('type', 'unknown'),
                        'volatility_tier': config.get('volatility_tier', 'unknown')
                    })
        return stocks
    
    def validate_strategy(self, stock_code):
        """驗證策略配置完整性"""
        config = self.load_strategy(stock_code)
        if not config:
            return False, "Strategy file not found"
        
        required_sections = ['entry', 'exit', 'position', 'risk']
        missing = []
        for section in required_sections:
            if section not in config:
                missing.append(section)
        
        if missing:
            return False, f"Missing sections: {', '.join(missing)}"
        
        return True, "OK"


class TinaBrainWithStockContext:
    """
    具備個股感知能力的 Tina 大腦
    繼承 StockStrategyLoader，針對不同股性進行精確決策
    """
    
    def __init__(self):
        self.loader = StockStrategyLoader()
        
    def think_with_stock_context(self, stock_code, objective, market_data=None):
        """
        帶入個股上下文的大腦思考
        """
        # Step 1: 載入個股策略
        strategy = self.loader.load_strategy(stock_code)
        if not strategy:
            return {
                'status': 'error',
                'message': f'找不到股票 {stock_code} 的策略配置'
            }
        
        # Step 2: 取得個股特徵（讓 MiniMax 知道正在處理哪檔股票）
        character = self.loader.get_stock_character(stock_code)
        instructions = self.loader.get_brain_instructions(stock_code)
        
        # Step 3: 建構思考上下文
        context = {
            'stock_code': stock_code,
            'stock_name': strategy.get('name', ''),
            'stock_character': character,
            'volatility_tier': strategy.get('volatility_tier', 'medium'),
            'brain_instructions': instructions,
            'objective': objective,
            'market_data': market_data or {}
        }
        
        # Step 4: 進行慢思考（CoT）
        thought_log = self._build_thought_chain(stock_code, objective, context)
        
        # Step 5: 自我博弈（如需要修改參數）
        decision = {
            'stock_code': stock_code,
            'action': objective,
            'confidence': 0.7,
            'context': context
        }
        
        # 根據是否涉及參數修改，決定是否需要委員會
        needs_committee = any(keyword in objective for keyword in ['修改', '調整', '改參數'])
        
        return {
            'status': 'complete',
            'stock_code': stock_code,
            'stock_character': character,
            'volatility_tier': strategy.get('volatility_tier'),
            'thought_log': thought_log,
            'brain_instructions': instructions,
            'decision': decision,
            'requires_committee': needs_committee
        }
    
    def _build_thought_chain(self, stock_code, objective, context):
        """建構思考鏈"""
        character = context['stock_character']
        instructions = context['brain_instructions']
        
        log = []
        log.append(f"【個股確認】正在分析 {stock_code} ({context['stock_name']})")
        log.append(f"【股性識別】{character.get('label', 'unknown')} - {character.get('bias', 'unknown')}")
        log.append(f"【波動等级】{context['volatility_tier']}")
        log.append(f"【目標】{objective}")
        
        # 根據股性加入特定思考
        if instructions.get('think_context'):
            log.append(f"【個股特徵】{instructions['think_context']}")
        
        if instructions.get('avoid_mistakes'):
            log.append(f"【避免錯誤】{instructions['avoid_mistakes']}")
        
        return log
    
    def modify_strategy_only_for_stock(self, stock_code, new_params, reason):
        """
        僅修改指定股票的策略（防止跨股污染）
        """
        # 驗證
        strategy = self.loader.load_strategy(stock_code)
        if not strategy:
            return False, f"股票 {stock_code} 策略不存在"
        
        # 檢查修改頻率（防止頻繁修改）
        # TODO: 實作計數器邏輯
        
        # 僅修改指定欄位
        for section, params in new_params.items():
            if section in strategy:
                if isinstance(params, dict):
                    strategy[section].update(params)
                else:
                    strategy[section] = params
        
        # 寫回檔案（新建版本而非直接覆寫）
        version = self._get_next_version(stock_code)
        backup_path = os.path.join(self.strategies_dir, f'backup', f'{stock_code}_v{version}.json')
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # 儲存備份
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)
        
        # 更新主要檔案
        main_path = os.path.join(self.strategies_dir, f'{stock_code}.json')
        with open(main_path, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)
        
        # 清除快取
        if stock_code in self.loader.cache:
            del self.loader.cache[stock_code]
        
        return True, f"已更新 {stock_code} v{version}，原因: {reason}"
    
    def _get_next_version(self, stock_code):
        """取得下一個版本號"""
        backup_dir = os.path.join(self.strategies_dir, 'backup')
        if not os.path.exists(backup_dir):
            return 1
        
        versions = []
        for f in os.listdir(backup_dir):
            if f.startswith(f'{stock_code}_v'):
                try:
                    v = int(f.replace(f'{stock_code}_v', '').replace('.json', ''))
                    versions.append(v)
                except:
                    pass
        
        return max(versions) + 1 if versions else 1


if __name__ == '__main__':
    loader = StockStrategyLoader()
    
    # 測試載入
    print("=== 已配置的股票 ===")
    stocks = loader.list_all_stocks()
    for s in stocks[:10]:
        print(f"  {s['code']} {s['name']} ({s['market']}) - {s['volatility_tier']}")
    
    # 測試個股感知
    print("\n=== 2330 台積電 策略 ===")
    strategy = loader.load_strategy('2330')
    print(f"名稱: {strategy['name']}")
    print(f"股性: {strategy['stock_character']}")
    print(f"ATR倍數: {strategy['stock_character'].get('atr_multiplier', 1.0)}")
    
    # 測試大腦
    print("\n=== 帶個股感知的大腦思考 ===")
    brain = TinaBrainWithStockContext()
    result = brain.think_with_stock_context('2330', '分析是否應該進場', {'price': 2135, 'rsi': 62.6})
    for line in result['thought_log']:
        print(line)