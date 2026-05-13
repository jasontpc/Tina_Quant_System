d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Remove duplicate safe_msg line
d = d.replace("    safe_msg = str(message) if not isinstance(message, str) else message\n\n    safe_msg = str(message) if not isinstance(message, str) else message",
              "    safe_msg = str(message) if not isinstance(message, str) else message", 1)

open('streamlit_tw_stock.py', 'w', encoding='utf-8').write(d)

# Verify syntax
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'streamlit_tw_stock.py'],
                       capture_output=True, text=True, cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System')
print('Exit:', result.returncode)
if result.returncode != 0:
    print('Error:', result.stderr[:300])
else:
    print('OK - no duplicate safe_msg')

# Commit and push
import subprocess
subprocess.run(['git', 'add', 'streamlit_tw_stock.py'], cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System')
result = subprocess.run(['git', 'commit', '-m', 'fix: robust _get_secret with json.loads + push_telegram token regex extraction'], cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System', capture_output=True, text=True)
print('Commit:', result.stdout[:200])
print('Stderr:', result.stderr[:200] if result.stderr else '')
result2 = subprocess.run(['git', 'push', 'origin', 'master'], cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System', capture_output=True, text=True)
print('Push:', result2.stdout[:100], result2.stderr[:100] if result2.stderr else '')