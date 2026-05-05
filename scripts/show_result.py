import pandas as pd
df = pd.read_csv(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_growth_under_100_full.csv', encoding='utf-8-sig')
print('Total rows:', len(df))
print('Signal breakdown:')
print(df['訊號'].value_counts())
print()
print('Top stocks by score:')
for _, r in df.iterrows():
    sig = r['訊號']
    sid = r['代號']
    price = r['現價']
    rsi = r['RSI']
    rev = r['營收成長%']
    pe = r['PE']
    roe = r['ROE%']
    score = r['分數']
    print(f"{sig:12} | {sid:5} | ${price} | RSI={rsi} | Rev={rev}% | PE={pe} | ROE={roe}% | Score={score}")