# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Change to nana directory
import os
os.chdir(os.path.join(ROOT, 'teams', 'nana'))

import nana_v5
system = nana_v5.NanaSystem()
system.run()