"""Debug: run econ_web_learning and capture full output"""
import sys, io

# Capture stdout
old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    import ray_econ_learner as m
    result = m.econ_web_learning()
    output = sys.stdout.getvalue()
finally:
    sys.stdout = old_stdout

print("=== STDOUT ===")
print(output)
print("=== RESULT ===")
print(result)
print("=== DB CHECK ===")
import sqlite3
conn = sqlite3.connect(r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE symbol=?', ('WEB_SOURCE',))
print('WEB_SOURCE count:', c.fetchone()[0])
conn.close()