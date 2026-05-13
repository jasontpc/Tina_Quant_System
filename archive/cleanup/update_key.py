import re

with open('vegas_scan.py', 'rb') as f:
    raw = f.read()

text = raw.decode('cp950', errors='replace')

text = text.replace('YOUR_API_KEY', 'FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF')
text = text.replace('YOUR_API_SECRET', '3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW')

with open('vegas_scan.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('done')