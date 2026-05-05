# Remove delisted 2888 from VALID_STOCKS
with open('nana_light.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'2888',", '')

with open('nana_light.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('2888 removed from nana_light.py VALID_STOCKS')

# Remove from nana_v64.py too
with open('nana_v64.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'2888',", '')

with open('nana_v64.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('2888 removed from nana_v64.py VALID_STOCKS')

# Clear stale cache
import os
for f in ['scan_cache.json', 'scan_cache_v64.json']:
    if os.path.exists(f):
        os.remove(f)
        print(f'Cache {f} cleared')