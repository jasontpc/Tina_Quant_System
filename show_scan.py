d = open('teams/leadtrades/leos/leos_v65.py', encoding='utf-8').read()
lines = d.split('\n')

# Show lines 130 to 350 to see the full scan loop
for i in range(130, min(len(lines), 380)):
    l = lines[i]
    if l.strip():
        print(f'{i+1}: {l[:100]}')