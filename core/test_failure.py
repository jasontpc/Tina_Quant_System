# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
from core import failure_analysis
fa = failure_analysis.FailureAnalyzer()
fa._ensure_csv()  # recreate
import os, csv
# write sample rows
os.makedirs(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data', exist_ok=True)
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\failure_log.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['id','code','name','entry_date','exit_date','entry_price','exit_price','return_pct','rsi_entry','atr_entry','atr_pct','bias','volume_ratio','f_days_before','t_days_before','failure_type','failure_reason','market_status','notes','system_version'])
    rows = [
        ['897eae10','3231','緯創','2026-04-10','2026-04-17','142.0','136.5','-3.87','77.3','4.1','2.9','8.2','0.9','4','0','INST_REVERSAL','RSI過熱進場(77.3); 法人逆轉(買超後突然賣出); 市場過熱/多頭尾端; 跌破ATR停損(-3.9%); MA20偏離過大(8.2%); 量能不足(VR=0.90)','OVERBOUGHT','法人連續買超後突然賣出，RSI>75進場過熱','Nana_v5.0'],
        ['aa78ee63','3017','奇鋐','2026-04-08','2026-04-15','2650.0','2570.0','-3.02','68.5','120.0','4.5','12.1','0.8','0','6','MA_BREAK','RSI偏高進場(68.5); 市場過熱/多頭尾端; 跌破ATR停損(-3.0%); MA20偏離過大(12.1%); 量能不足(VR=0.80); MA20均線跌破','OVERBOUGHT','MA20偏離過大12%，市場過熱時跌破均線','Nana_v5.0'],
        ['deec8d80','2379','瑞昱','2026-04-05','2026-04-11','520.0','500.0','-3.85','72.1','15.0','2.9','5.3','0.7','3','0','STOP_LOSS','RSI偏高進場(72.1); 跌破ATR停損(-3.9%); 量能不足(VR=0.70)','NEUTRAL','量能不足，進場後缺乏支撐','Nana_v5.0'],
    ]
    for r in rows:
        w.writerow(r)
report = fa.generate_report()
fa.print_report(report)