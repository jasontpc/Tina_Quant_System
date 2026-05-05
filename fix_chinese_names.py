# -*- coding: utf-8 -*-
"""Fix: Chinese brand names as primary search key"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Update all brand_name to use Chinese (where available)
updates = {
    # 1F Beauty
    'Chanel': '香奈兒',
    'Dior': '迪奧',
    'Louis Vuitton': '路易威登',
    'Hermès': '愛馬仕',
    'Fendi': '芬迪',
    'Yves Saint Laurent': '伊夫聖羅蘭',
    'Giorgio Armani': '喬治阿瑪尼',
    'Tom Ford': '湯姆福特',
    'NARS': 'NARS 彩妝',
    'SK-II': 'SK-II 護膚神仙水',
    'La Mer': '海藍之謎',
    'La Prairie': '瑞士萊珀妮',
    'Estée Lauder': '雅詩蘭黛',
    'LANCÔME': '蘭蔻',
    "Kiehl's": '科顏氏',
    'Guerlain': '嬌蘭',
    'Bourjois': '巴黎腮紅',
    'Swiss Perfection': '瑞士perf',
    'Le Labo': '實驗室香水',
    'The Hour Glass': '時間之廊',
    'Clé de Peau': '肌膚之鑰',
    'Shu Uemura': '植村秀',
    'Decathlon': '迪卡儂',
    # 2F Watches
    'Cartier': '卡地亞',
    'Van Cleef & Arpels': '梵克雅寶',
    'Tiffany & Co.': '蒂芙尼',
    'Bulgari': '寶格麗',
    'Graff': '格拉夫',
    'Chaumet': '尚美巴黎',
    'FRED': '弗萊德',
    'Damiani': '玳美雅',
    'Buccellati': '蒲伊她',
    'Boucheron': '伯敘',
    'Patek Philippe': '百達翡麗',
    'Vacheron Constantin': '江詩丹頓',
    'Breguet': '寶璣',
    'Rolex': '勞力士',
    'OMEGA': '歐米茄',
    'IWC': '萬國錶',
    'Piaget': '伯爵',
    'Jaquet Droz': '雅克德羅',
    'TAG Heuer': '泰格豪雅',
    'Grand Seiko': 'Grand Seiko',
    'Longines': '浪琴',
    'Tudor': '帝舵',
    'Moncler': '盟可睞',
    'Jimmy Choo': '周仰傑',
    'Celine': '賽琳',
    'Loewe': '羅威',
    'Loro Piana': '諾悠翩雅',
    'KENZO': '凱卓',
    'Marc Jacobs': '馬克雅各',
    'Acne Studios': 'Acne Studios',
    'Ami Paris': 'Ami Paris',
    'A.P.C.': 'A.P.C.',
    'Isabel Marant': 'Isabel Marant',
    'BOSS': 'BOSS 西裝',
    'J.ESTINA': 'J.ESTINA 首飾',
    # 3F Contemporary
    'Ader Error': 'Ader Error 韓系',
    'Sandro': 'Sandro 法國女裝',
    'Maje': 'Maje 法國女裝',
    'Claudie Pierlot': 'Claudie Pierlot 法國女裝',
    'IRO': 'IRO 法國品牌',
    'The Row': 'The Row 極簡',
    'Totême': 'Totême 北歐品牌',
    'Ganni': 'Ganni 丹麥女裝',
    'Ba&sh': 'Ba&sh 法國女裝',
    'Self-Portrait': 'Self-Portrait 英國品牌',
    'Miss Sixty': 'Miss Sixty 義大利女裝',
    "O'2nd": 'O\'2nd 韓系女裝',
    'SJSJ': 'SJSJ 韓系女裝',
    'Uniqlo': '優衣庫',
    'Gap': 'Gap 美式休閒',
    'Tommy Hilfiger': '湯米希爾菲格',
    'Calvin Klein': '卡文克萊',
    # 4F Sports
    'The North Face': '北面/湯北',
    'Columbia': '哥倫比亞戶外',
    'Salomon': '薩洛蒙',
    "Arc'teryx": '始祖鳥',
    'Patagonia': '巴塔哥尼亞',
    'Mammut': '猛獁象',
    'La Sportiva': '拉斯珀蒂娃',
    'Black Diamond': '黑鑽',
    'Nike': 'Nike 耐吉',
    'Adidas': 'Adidas 愛迪達',
    'New Balance': 'New Balance 新百倫',
    'Converse': 'Converse 匡威',
    'Vans': 'Vans 范斯',
    'Fila': 'Fila 斐樂',
    'Puma': 'Puma 彪馬',
    'Asics': 'Asics 亚瑟士',
    'Under Armour': '安德瑪',
    'Descente': '迪桑特',
    'Le Coq Sportif': '法國公雞',
    'Kappa': 'Kappa 卡帕',
    # 5F Mens
    'Brioni': '布里奥尼',
    'Ermenegildo Zegna': '傑尼亞',
    'Ralph Lauren': '拉夫勞倫',
    'Canali': '卡拉尼',
    'Finamore': '菲娜莫爾',
    'Drakes': '德雷克斯',
    'Jil Stuart': '吉爾斯圖亞特',
    "Tricker's": '特里克爾斯',
    'Berluti': '伯爾魯帝',
    'John Lobb': '約翰洛布',
    'Crockett & Jones': 'Crockett & Jones',
    # 6F Kids
    'Baby Dior': '迪奧童裝',
    'Burberry Kids': '巴宝莉童裝',
    'Fendi Kids': '芬迪童裝',
    'Moncler Enfant': '盟可睞童裝',
    'Armani Junior': '阿瑪尼童裝',
    'Ralph Lauren Children': '拉夫勞倫童裝',
    'Gap Kids': 'Gap童裝',
    'Nike Kids': 'Nike童裝',
    'Adidas Kids': 'Adidas童裝',
    'Converse Kids': 'Converse童裝',
    'KidZania': '奇贊比亞',
    'Callaway': '卡拉威',
    'Titleist': 'Titleist 高爾夫',
    'TaylorMade': '泰勒梅',
    'PING': 'PING 高爾夫',
    'Foot Joy': 'FootJoy',
    'Lacoste': ' LACOSTE 鱷魚',
    # 7F Electronics
    'Samsung': '三星電子',
    'LG': 'LG電子',
    'Apple': 'Apple 蘋果',
    'Dyson': '戴森',
    'CGV': 'CGV 影城',
    'LEGO': 'LEGO 樂高',
    'Pottery Barn Kids': 'Pottery Barn Kids',
    # 8F
    'IKEA': '宜家家居',
    'CGV IMAX': 'CGV IMAX',
    # B1
    'Bottega Veneta': 'Bottega Veneta 葆蝶家',
    'Goyard': 'Goyard 戈雅',
    'Prada': 'Prada 普拉達',
    'Moynat': 'Moynat 莫奈',
    'Mul': 'Mul 穆勒',
    'Parosh': 'Parosh 派洛斯',
    'Covernat': 'Covernat 庫弗納特',
    'ABC-MART': 'ABC-MART 鞋店',
    'New Balance': 'New Balance 新百倫',
    'Hummel': 'Hummel 休閒',
    # B2
    'LX Z:IN': 'LX Z:IN',
}

count = 0
for en_name, cn_name in updates.items():
    cur.execute('UPDATE brands SET brand_name=? WHERE brand_name_en=? OR brand_name=?', 
                (cn_name, en_name, en_name))
    if cur.rowcount > 0:
        count += 1

conn.commit()
print(f'Updated {count} brand names to Chinese')

# Verify
cur.execute('SELECT brand_name, category, subcategory FROM brands ORDER BY brand_name LIMIT 30')
print('\nSample brands:')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]}/{r[2]}')

# Search test
print('\n=== Search Test ===')
tests = ['香奈兒', 'Nike', '卡地亞', '北面', '迪奧', '童裝', '高爾夫', '珠寶']
for q in tests:
    like = f'%{q}%'
    cur.execute('''SELECT brand_name, category, subcategory FROM brands 
        WHERE brand_name LIKE ? OR brand_name_ko LIKE ? OR brand_name_en LIKE ?
        ORDER BY brand_name LIMIT 5''', (like, like, like))
    rows = cur.fetchall()
    print(f'\n"{q}": {len(rows)} results')
    for r in rows:
        print(f'  [{r[0]}] {r[1]}/{r[2]}')

conn.close()
print('\nDone!')