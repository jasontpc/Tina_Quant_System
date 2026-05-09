"""
Macro-to-Short-Term Memory Bridge
==================================
功能：Macro Jobs 執行後，自動寫入短期記憶（short_term）

用法（作為 macro_job 的一部分）：
  from macro_st_memory_bridge import MacroSTM bridge
  bridge.write_macro_observation(macro_json_path, job_name='晨間快報')

在 isolated job 的 python 腳本最後呼叫：
  python -c "from stores.macro_st_bridge import MacroSTBridge; \
    MacroSTBridge().write_macro_observation('reports/macro/20260508_morning.json', '晨間快報')"
"""

import sys, json
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
sys.path.insert(0, str(BASE_DIR))

from stores.short_term_writer import write_memory

class MacroSTBridge:
    """將 Macro Job 輸出橋接到短期記憶"""
    
    def __init__(self):
        self.base_dir = BASE_DIR
    
    def write_macro_observation(self, macro_json_path: str, job_name: str = 'macro_job') -> str:
        """
        讀取 Macro JSON，寫入短期記憶 observation
        """
        macro_file = Path(macro_json_path)
        if not macro_file.exists():
            print(f'[Bridge] File not found: {macro_json_path}')
            return None
        
        with open(macro_file, 'r', encoding='utf-8') as f:
            macro = json.load(f)
        
        # 提取關鍵摘要
        market = macro.get('market_data', {})
        twii = market.get('TWII', {})
        vix = market.get('VIX', {})
        dxy = market.get('DXY', {})
        yield_ = market.get('yield_10y', {})
        
        # 地緣政治摘要（取前100字）
        geo = macro.get('geopolitical', {})
        geo_summary = geo.get('summary', '')[:100] if geo.get('summary') else '無重大地緣風險'
        
        # 趨勢主題
        themes = macro.get('thematic_trends', {})
        theme_tags = [t.get('theme', '') for t in themes.get('trends', [])[:3]]
        
        # 組合 summary
        twii_change = twii.get('change_pct', 0)
        vix_val = vix.get('current', 0)
        
        summary = f"TWII: {twii.get('current','N/A')} ({twii_change:+.1f}%) | VIX: {vix_val} | 地緣: {geo_summary[:40]}"
        
        # 寫入短期記憶
        memory_id = write_memory(
            mtype='observation',
            summary=summary,
            detail=json.dumps({
                'job_name': job_name,
                'macro_file': str(macro_file.name),
                'market_data': market,
                'geopolitical_summary': geo.get('summary', ''),
                'taiwan_impact': macro.get('taiwan_impact', {}),
                'thematic_trends': themes,
                'confidence': macro.get('confidence', {}),
                'forecast_direction': macro.get('forecast', {}).get('direction', 'neutral')
            }, ensure_ascii=False),
            source='macro_job',
            tags=['macro', 'TWII', 'VIX'] + theme_tags,
            importance=self._calc_importance(twii_change, vix_val),
            links=[],
            expiry_days=30
        )
        
        print(f'[MacroBridge] Written: {memory_id}')
        return memory_id
    
    def _calc_importance(self, twii_change_pct: float, vix: float) -> int:
        """根據市場波動計算重要性"""
        score = 5
        if abs(twii_change_pct) > 1.5:
            score += 2
        elif abs(twii_change_pct) > 1.0:
            score += 1
        
        if vix > 25:
            score += 2
        elif vix > 20:
            score += 1
        
        return min(10, score)
    
    def write_macro_decision(self, macro_json_path: str, action: str, reason: str, confidence: int) -> str:
        """
        寫入 Macro 相關的交易決定（如果有）
        """
        return write_memory(
            mtype='decision',
            summary=f"Macro action: {action} | {reason}",
            detail=f"Confidence: {confidence}/10",
            source='macro_decision',
            tags=['macro', 'strategic'],
            importance=confidence,
            links=[]
        )

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', required=True)
    parser.add_argument('--job', '-j', default='macro_job')
    args = parser.parse_args()
    
    bridge = MacroSTBridge()
    bridge.write_macro_observation(args.file, args.job)