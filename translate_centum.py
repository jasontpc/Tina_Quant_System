# -*- coding: utf-8 -*-
"""Shinsegae Centum City - Translate to Traditional Chinese"""
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# ========================
# FLOOR TRANSLATIONS (Korean → Traditional Chinese)
# ========================
FLOOR_NAME_KO_TO_TC = {
    '지하 2층': '地下二樓',
    '지하 1층': '地下一樓',
    '1층': '一樓',
    '2층': '二樓',
    '3층': '三樓',
    '4층': '四樓',
    '5층': '五樓',
    '6층': '六樓',
    '7층': '七樓',
    '8층': '八樓',
    '9층': '九樓',
    '10층': '十樓',
    '11층': '十一樓',
}

FLOOR_DESC_KO_TO_TC = {
    # B2
    '하이퍼그라운드/주차장': 'Hyper Ground/停車場',
    '신세계팩토리스토어': '新世界Factory Store',
    '영풍문고': '永豐文庫',
    # B1
    '푸드마켓/패션잡화/핸드백/이벤트홀': '美食廣場/流行雜貨/手提包/活動廳',
    '스포츠 슈 전문관': '運動鞋專門館',
    # 1F
    '해외유명브랜드/화장품/스파랜드': '海外知名品牌/化妝品/SPA館',
    '스포츠/아웃도어': '運動/戶外',
    # 2F
    '해외유명브랜드/워치/여성': '海外知名品牌/腕錶/女性',
    '스포츠/캐주얼': '運動/休閒',
    # 3F
    '컨템포러리/국내여성': '當代設計/韓國女性',
    '라이프스타일/까사미아': '生活風格/ Casa MIA',
    # 4F
    '뉴컨템퍼러리/란제리': 'New Contemporary/內衣',
    '아이스링크': 'Ice Link 冰上樂園',
    '파미에스테이션(푸드)': 'Pampers Station(美食)',
    # 5F
    '남성/씨네드쉐프': '男性/西裝',
    '남성 명품관': '男性精品館',
    # 6F
    '골프/아동/신세계 갤러리': '高爾夫/兒童/新世界Gallery',
    '신세계 아카데미': '新世界 Academy',
    '키자니아': 'KidZania',
    # 7F
    '생활(가전,홈패션)/CGV': '生活(家電,居家)/CGV',
    'PSA/S가든': 'PSA/S Garden',
    # 8F
    '생활(가구,인테리어)': '生活(家具,室內設計)',
    # 9F
    '전문식당가/문화홀/주라지/고객서비스센터': '專業餐廳區/文化廳/ZOO/客戶服務中心',
    # 10F
    '트리니티클럽&스파': 'Trinity Club & Spa',
    # 11F
    '골프레인지': 'Golf Range',
}

# ========================
# BRAND TRANSLATIONS (Korean → Traditional Chinese)
# ========================
BRAND_KO_TO_TC = {
    # Luxury / Fashion (1F)
    '루이비통': '路易威登',
    '에르메스': '愛馬仕',
    '디올': '迪奧',
    '보테가베네타': 'Bottega Veneta',
    '펜디': '芬迪',
    '버버리': 'Burberry',
    '발렌시아가': 'Balenciaga',
    '샤넬': '香奈兒',
    '입생로랑': 'Yves Saint Laurent',
    '조르지오아르마니': 'Giorgio Armani',
    '샤넬': '香奈兒',
    # Beauty (1F)
    'NARS': 'NARS',
    '라프리': 'La Prairie',
    '라메르': 'La Mer',
    '에스티로더': 'Estée Lauder',
    '랑콤': 'LANCÔME',
    'SK-Ⅱ': 'SK-II',
    '키엘': 'Kiehl\'s',
    '겔랑': 'Guerlain',
    '뽀아레': 'Bourjois',
    '스위스퍼펙션': 'Swiss Perfection',
    '르라보': 'Le Labo',
    '톰FORD': 'Tom Ford',
    # Watches / Jewelry (2F)
    '몽클레르': 'Moncler',
    '로에베': 'Loewe',
    '지미추': 'Jimmy Choo',
    '토즈': 'Tod\'s',
    '셀린느': 'Celine',
    '로로피아나': 'Loro Piana',
    '아르켓': 'Acne Studios',
    '겐조': 'KENZO',
    '마크모스': 'Marc Jacobs',
    '라다시오': 'Radaacio',
    '까르띠에': '卡地亞',
    '불가리': 'Bulgari',
    '반클리프앤아펠': 'Van Cleef & Arpels',
    '티파니': 'Tiffany & Co.',
    '그라프': 'Graff',
    '부첼라티': 'Buccellati',
    '다미아니': 'Damiani',
    'fred': 'FRED',
    '쇼메': 'Chaumet',
    '부쉐론': 'Boucheron',
    '파텍필립': 'Patek Philippe',
    '바쉐론콘스탄틴': 'Vacheron Constantin',
    '브레게': 'Breguet',
    '롤렉스': '勞力士',
    '오메가': 'OMEGA',
    'IWC': 'IWC 萬國錶',
    '피아제': 'Piaget',
    '위블로': 'Jaquet Droz',
    '태그호이어': 'TAG Heuer',
    '시슬': 'Cecil',
    '보스': 'BOSS',
    '아만시': 'Amass',
    # Contemporary / Korean (3F)
    '가니': 'Ganni',
    '아더에러': 'Ader Error',
    '송지오': 'Songzhi',
    '산드로': 'Sandro',
    'IRO': 'IRO',
    '제임스퍼소': 'James Persso',
    'edenthoe': 'Edên Hoe',
    '켄디드': 'Candied',
    '로엠': 'Louvement',
    '립스': 'Lips',
    '비비안': 'Vivien',
    '밀}': 'Mil',
    '데希腊': 'DeHells',
    # Sports / Outdoor (4F)
    '노스페이스': 'The North Face',
    '컬럼비아': 'Columbia',
    '살로몸': 'Salomon',
    '휠라': 'Fila',
    '유니클로': 'UNIQLO',
    '컨버스': 'Converse',
    'NIKE': 'Nike',
    'ADIDAS': 'Adidas',
    '뉴발란스': 'New Balance',
    '반스': 'Vans',
    '렉토': 'Recto',
    '킨': 'Kin',
    '밀': 'Mil',
    '온': 'O',
    '더자이': 'The Sauce',
    '시스템': 'System',
    '롱슈': 'Longshirt',
    '모에나': 'Moena',
    '레노': 'Reno',
    '에버': 'Ever',
    '아가타': 'Agatha',
    # Men's Luxury (5F)
    '알페른': 'Alpen',
    '랜드로버': 'Land Rover',
    '드레이크스': 'Drakes',
    '질스튜어트': 'Jil Stuart',
    'antoine': 'Antoine',
    '보테가': 'Bottega',
    '보calia': 'Bocali',
    '루이': 'Louis',
    # Kids (6F)
    '베이비디올': 'Baby Dior',
    '몽클레르앙팡': 'Moncler Enfant',
    '버버리칠드런': 'Burberry Children',
    '펜디키즈': 'Fendi Kids',
    '겐조키즈': 'KENZO Kids',
    '엠포리오아르마니주니어': 'Emporio Armani Junior',
    '랄프로렌칠드런': 'Ralph Lauren Children',
    '톰보이': 'Tom Boy',
    '발레': 'Ballet',
    'GAP': 'GAP',
    '几家': 'Jiia',
    # Tech / Life (7F-8F)
    '삼성': '三星電子',
    'LG': 'LG電子',
    # Restaurants (9F)
    '한식': '韓式料理',
    '중식': '中式料理',
    '일식': '日式料理',
    '양식': '西式料理',
    '뷔페': '自助餐',
    '카페': '咖啡廳',
    # Services
    '키자니아': 'KidZania',
    '신세계 아카데미': '新世界 Academy',
    '신세계 갤러리': '新世界 Gallery',
    # Mall / Books
    '영풍문고': '永豐文庫',
    '신세계팩토리스토어': '新世界 Factory Store',
    'LX Z:IN': 'LX Z:IN',
    # Beauty Retail
    '올리브영': 'Olive Young',
    '아모레': 'Amore',
    '화장': '化妝品',
    '키스미': 'Kiss Me',
    'VT': 'VT',
    'cosrx': 'COSRX',
    'anev': 'ANEV',
    '에센': 'Essence',
    '리얼버화': 'Real Barrier',
    '메르치': 'Melche',
    '산아': 'Sana',
    '스와니': 'Suanni',
    # Miscelaneous
    '.mul': 'Mull',
    '고야드': 'Goyard',
    '쁘빠': 'Ppappa',
    '에뷔이어스': 'Eviuso',
    '오버데크': 'Overdek',
    '프라다': 'Prada',
    '톰FORD': 'Tom Ford',
    '제이에스티나': 'J.ESTINA',
    '드레이크스': 'Drakes',
}

def translate_floor_name(ko):
    return FLOOR_NAME_KO_TO_TC.get(ko, ko)

def translate_floor_desc(desc):
    if not desc:
        return desc
    result = desc
    for ko, tc in FLOOR_DESC_KO_TO_TC.items():
        result = result.replace(ko, tc)
    return result

def translate_brand(name):
    if not name:
        return name
    return BRAND_KO_TO_TC.get(name.strip(), name.strip())

# ========================
# UPDATE FLOORS
# ========================
print('Translating floors...')
cur.execute('SELECT id, name_ko, description FROM floors')
for row in cur.fetchall():
    fid, name_ko, desc = row
    new_name = translate_floor_name(name_ko)
    new_desc = translate_floor_desc(desc)
    cur.execute('UPDATE floors SET name_ko=?, description=? WHERE id=?', (new_name, new_desc, fid))

# ========================
# UPDATE BRANDS (translate Korean → TC)
# ========================
print('Translating brands...')
cur.execute('SELECT id, brand_name, brand_name_ko FROM brands')
for row in cur.fetchall():
    bid, name, name_ko = row
    # Prefer brand_name if English, use Korean→TC dict
    tc_name = translate_brand(name_ko) if name_ko else translate_brand(name)
    if tc_name and tc_name != name:
        cur.execute('UPDATE brands SET brand_name=?, brand_name_ko=? WHERE id=?', (tc_name, tc_name, bid))

conn.commit()

# ========================
# VERIFY
# ========================
print('\n=== TRANSLATED FLOORS ===')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]}')
    print(f'       {r[2]}')

print('\n=== BRANDS BY FLOOR ===')
cur.execute('SELECT floor, COUNT(*) FROM brands GROUP BY floor ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]} brands')

print('\n=== SAMPLE: 1F BRANDS ===')
cur.execute('SELECT brand_name FROM brands WHERE floor="1F" ORDER BY brand_name')
for r in cur.fetchall():
    print(f'  {r[0]}')

print('\n=== SAMPLE: 2F BRANDS ===')
cur.execute('SELECT brand_name FROM brands WHERE floor="2F" ORDER BY brand_name LIMIT 20')
for r in cur.fetchall():
    print(f'  {r[0]}')

print('\n=== SAMPLE: 4F BRANDS ===')
cur.execute('SELECT brand_name FROM brands WHERE floor="4F" ORDER BY brand_name')
for r in cur.fetchall():
    print(f'  {r[0]}')

print('\n=== SAMPLE: 6F BRANDS ===')
cur.execute('SELECT brand_name FROM brands WHERE floor="6F" ORDER BY brand_name')
for r in cur.fetchall():
    print(f'  {r[0]}')

conn.close()
print('\nDone!')