# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_cn_main.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all links
links = re.findall(r'href=["\'](.*?)["\']', html)
centum = [l for l in links if 'centum' in l.lower() or 'CENTUM' in l or 'busan' in l.lower()]
print('Centum links:')
for l in centum[:20]:
    print(f'  {l}')

print()
# Find data attributes with store codes
codes = re.findall(r'data-store|storeCode|store_id', html[:5000])
print('Store code refs:', codes[:10])

# Find the Centum City section
idx = html.lower().find('centum')
if idx >= 0:
    print(f'\nCentum context (chars {idx-100}:{idx+200}):')
    print(html[idx-100:idx+200])
