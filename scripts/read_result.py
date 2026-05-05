import pandas as pd
df = pd.read_csv(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_growth_under_100_full.csv', encoding='utf-8-sig')
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_result.txt', 'w', encoding='utf-8') as f:
    for _, r in df.iterrows():
        f.write(f"{r['代號']},{r['現價']},{r['RSI']},{r['PE']},{r['ROE%']},{r['營收成長%']},{r['MA狀態']},{r['MA20偏離%']},{r['分數']},{r['訊號']}\n")
print('Rows:', len(df))
print('Signals:', df['訊號'].value_counts().to_dict())