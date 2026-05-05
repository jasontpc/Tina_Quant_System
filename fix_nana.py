content = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\nana_autonomous_develop.py', 'r', encoding='utf-8').read()
content = content.replace(
    "{ENTRY_PARAMS['RSI_max'].get(regime, 65)}",
    "{ENTRY_PARAMS['RSI_max'].get(current_regime, 65)}"
)
content = content.replace(
    "{ENTRY_PARAMS['RSI_max'].get(regime,",
    "{ENTRY_PARAMS['RSI_max'].get(current_regime,"
)
open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\nana_autonomous_develop.py', 'w', encoding='utf-8').write(content)
print('fixed')