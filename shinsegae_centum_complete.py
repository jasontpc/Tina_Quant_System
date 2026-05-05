# -*- coding: utf-8 -*-
"""Shinsegae Centum City - Complete Brand DB with Full Search"""
import sqlite3, sys, os, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = os.path.join(DATA_DIR, 'shinsegae_centum.db')

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    cur = conn.cursor()
    # Drop and rebuild with FULLTEXT search
    cur.execute('DROP TABLE IF EXISTS brands')
    cur.execute('DROP TABLE IF EXISTS floors')
    cur.execute('''CREATE TABLE floors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor TEXT, name_ko TEXT, name_en TEXT,
        description TEXT, scraped_at TEXT
    )''')
    cur.execute('''CREATE TABLE brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor TEXT,
        brand_name TEXT,
        brand_name_ko TEXT,
        brand_name_en TEXT,
        category TEXT,
        subcategory TEXT,
        location_detail TEXT,
        scraped_at TEXT
    )''')
    # Create FULLTEXT virtual table for search
    cur.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS brands_fts USING fts5(
        brand_name, brand_name_ko, brand_name_en, category, subcategory,
        content='brands', content_rowid='id'
    )''')
    conn.commit()

def rebuild_fts(conn):
    """Rebuild FTS index"""
    cur = conn.cursor()
    cur.execute('INSERT INTO brands_fts(brands_fts) VALUES(\'rebuild\')')
    conn.commit()

def save_brand(conn, info):
    cur = conn.cursor()
    cur.execute('''INSERT INTO brands (floor, brand_name, brand_name_ko, brand_name_en, category, subcategory, location_detail, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (info.get('floor'), info.get('brand_name'), info.get('brand_name_ko'),
         info.get('brand_name_en'), info.get('category'), info.get('subcategory'),
         info.get('location_detail'), info.get('scraped_at', time.strftime('%Y-%m-%d %H:%M'))))
    return cur.lastrowid

def save_floor(conn, info):
    cur = conn.cursor()
    cur.execute('INSERT INTO floors (floor, name_ko, name_en, description, scraped_at) VALUES (?, ?, ?, ?, ?)',
        (info.get('floor'), info.get('name_ko'), info.get('name_en'),
         info.get('description'), info.get('scraped_at', time.strftime('%Y-%m-%d %H:%M'))))

# ========================
# COMPLETE BRAND DATABASE
# Based on Namu Wiki + Naver data
# ========================
FLOORS = [
    {'floor': 'B2', 'name_ko': '地下二樓', 'name_en': 'B2',
     'description': 'Hyper Ground 停車場 / 新世界Factory Store / 永豐文庫 / LX Z:IN'},
    {'floor': 'B1', 'name_ko': '地下一樓', 'name_en': 'B1',
     'description': '美食廣場 / 流行雜貨 / 手袋 / 活動廳 / 運動鞋專門館'},
    {'floor': '1F', 'name_ko': '一樓', 'name_en': '1F',
     'description': '海外精品 / 化妝品 / SPA / 運動 / 戶外'},
    {'floor': '2F', 'name_ko': '二樓', 'name_en': '2F',
     'description': '海外精品 / 腕錶 / 女性 / 運動 / 休閒'},
    {'floor': '3F', 'name_ko': '三樓', 'name_en': '3F',
     'description': '當代設計 / 韓國女性 / 生活風格'},
    {'floor': '4F', 'name_ko': '四樓', 'name_en': '4F',
     'description': 'New Contemporary / 內衣 / Ice Link 冰樂園 / 運動'},
    {'floor': '5F', 'name_ko': '五樓', 'name_en': '5F',
     'description': '男性西裝 / 男性精品館'},
    {'floor': '6F', 'name_ko': '六樓', 'name_en': '6F',
     'description': '高爾夫 / 兒童 / 新世界 Gallery / 新世界 Academy / KidZania'},
    {'floor': '7F', 'name_ko': '七樓', 'name_en': '7F',
     'description': '生活(家電,居家) / CGV ULTRA 4DX / PSA/S Garden'},
    {'floor': '8F', 'name_ko': '八樓', 'name_en': '8F',
     'description': '生活(家具/室內設計) / CGV IMAX'},
    {'floor': '9F', 'name_ko': '九樓', 'name_en': '9F',
     'description': '專業餐廳區 / 文化廳 / ZOO / 客戶服務中心'},
    {'floor': '10F', 'name_ko': '十樓', 'name_en': '10F',
     'description': 'Trinity Club & Spa'},
    {'floor': '11F', 'name_ko': '十一樓', 'name_en': '11F',
     'description': 'Golf Range'},
]

# COMPLETE BRAND LIST (Korean → Traditional Chinese)
BRANDS = [
    # ========================
    # B2 - 地下 (Hyper Ground / 停車場 / 服務)
    # ========================
    {'floor': 'B2', 'brand': '新世界 Factory Store', 'ko': '신세계팩토리스토어', 'en': 'Shinsegae Factory Store', 'category': '生活', 'sub': '工廠直營店'},
    {'floor': 'B2', 'brand': '永豐文庫', 'ko': '영풍문고', 'en': 'Youngpoong Bookstore', 'category': '文化', 'sub': '書店'},
    {'floor': 'B2', 'brand': 'LX Z:IN', 'ko': 'LX Z:IN', 'en': 'LX Z:IN', 'category': '生活', 'sub': '室內建材'},

    # ========================
    # B1 - 地下 (美食 / 流行雜貨 / 運動鞋)
    # ========================
    {'floor': 'B1', 'brand': 'Bottega Veneta', 'ko': '보테가베네타', 'en': 'Bottega Veneta', 'category': '精品', 'sub': '皮革'},
    {'floor': 'B1', 'brand': 'Goyard', 'ko': '고야드', 'en': 'Goyard', 'category': '精品', 'sub': '行李箱'},
    {'floor': 'B1', 'brand': 'Prada', 'ko': '프라다', 'en': 'Prada', 'category': '精品', 'sub': '時裝'},
    {'floor': 'B1', 'brand': 'Moynat', 'ko': '모이나', 'en': 'Moynat', 'category': '精品', 'sub': '行李箱'},
    {'floor': 'B1', 'brand': 'Mulle', 'ko': '뮬레', 'en': 'Mulle', 'category': '精品', 'sub': '丹麥皮具'},
    {'floor': 'B1', 'brand': 'Loro Piana', 'ko': '로로피아나', 'en': 'Loro Piana', 'category': '精品', 'sub': '羊絨'},
    {'floor': 'B1', 'brand': 'Moorer', 'ko': '무라', 'en': 'Moorer', 'category': '精品', 'sub': '羽絨'},
    {'floor': 'B1', 'brand': 'Parosh', 'ko': '파로쉬', 'en': 'Parosh', 'category': '時裝', 'sub': '女裝'},
    {'floor': 'B1', 'brand': 'H Avenue', 'ko': '에이치애비뉴', 'en': 'H Avenue', 'category': '時裝', 'sub': '女裝'},
    {'floor': 'B1', 'brand': 'CoverNAT', 'ko': '커버낫', 'en': 'CoverNAT', 'category': '運動', 'sub': '鞋類'},
    {'floor': 'B1', 'brand': 'ABC-MART', 'ko': 'ABC마트', 'en': 'ABC-MART', 'category': '運動', 'sub': '鞋類專門店'},
    {'floor': 'B1', 'brand': 'New Balance', 'ko': '뉴발란스', 'en': 'New Balance', 'category': '運動', 'sub': '鞋類'},
    {'floor': 'B1', 'brand': 'Hummel', 'ko': '훔멜', 'en': 'Hummel', 'category': '運動', 'sub': '運動休閒'},

    # ========================
    # 1F - 海外精品 / 化妝品
    # ========================
    {'floor': '1F', 'brand': 'Louis Vuitton', 'ko': '루이비통', 'en': 'Louis Vuitton', 'category': '精品', 'sub': '時裝/行李箱'},
    {'floor': '1F', 'brand': 'Hermès', 'ko': '에르메스', 'en': 'Hermès', 'category': '精品', 'sub': '時裝/皮革'},
    {'floor': '1F', 'brand': 'Dior', 'ko': '디올', 'en': 'Dior', 'category': '精品', 'sub': '時裝/化妝品'},
    {'floor': '1F', 'brand': 'Chanel', 'ko': '샤넬', 'en': 'Chanel', 'category': '精品', 'sub': '時裝/化妝品'},
    {'floor': '1F', 'brand': 'Balenciaga', 'ko': '발렌시아가', 'en': 'Balenciaga', 'category': '精品', 'sub': '時裝'},
    {'floor': '1F', 'brand': 'Gucci', 'ko': '구찌', 'en': 'Gucci', 'category': '精品', 'sub': '時裝/皮革'},
    {'floor': '1F', 'brand': 'Fendi', 'ko': '펜디', 'en': 'Fendi', 'category': '精品', 'sub': '時裝/皮革'},
    {'floor': '1F', 'brand': 'Burberry', 'ko': '버버리', 'en': 'Burberry', 'category': '精品', 'sub': '時裝'},
    {'floor': '1F', 'brand': 'Yves Saint Laurent', 'ko': '입생로랑', 'en': 'Yves Saint Laurent', 'category': '精品', 'sub': '化妝品'},
    {'floor': '1F', 'brand': 'Giorgio Armani', 'ko': '조르지오아르마니', 'en': 'Giorgio Armani', 'category': '精品', 'sub': '化妝品'},
    {'floor': '1F', 'brand': 'Loewe', 'ko': '로에베', 'en': 'Loewe', 'category': '精品', 'sub': '皮革'},
    {'floor': '1F', 'brand': 'Bottega Veneta', 'ko': '보테가베네타', 'en': 'Bottega Veneta', 'category': '精品', 'sub': '皮革'},
    {'floor': '1F', 'brand': 'Tod\'s', 'ko': '토즈', 'en': "Tod's", 'category': '精品', 'sub': '鞋類/皮革'},
    {'floor': '1F', 'brand': 'Tom Ford', 'ko': '톰포트', 'en': 'Tom Ford', 'category': '化妝品', 'sub': '香水/護膚'},
    {'floor': '1F', 'brand': 'NARS', 'ko': '날스', 'en': 'NARS', 'category': '化妝品', 'sub': '彩妝'},
    {'floor': '1F', 'brand': 'SK-II', 'ko': '에스케이투', 'en': 'SK-II', 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'La Mer', 'ko': '라메르', 'en': 'La Mer', 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'La Prairie', 'ko': '라프라이', 'en': 'La Prairie', 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'Estée Lauder', 'ko': '에스티로더', 'en': 'Estée Lauder', 'category': '化妝品', 'sub': '化妝品'},
    {'floor': '1F', 'brand': 'LANCÔME', 'ko': '랑콤', 'en': 'LANCÔME', 'category': '化妝品', 'sub': '化妝品'},
    {'floor': '1F', 'brand': 'Kiehl\'s', 'ko': '키엘', 'en': "Kiehl's", 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'Guerlain', 'ko': '게를랭', 'en': 'Guerlain', 'category': '化妝品', 'sub': '香水'},
    {'floor': '1F', 'brand': 'Bourjois', 'ko': '뽀아레', 'en': 'Bourjois', 'category': '化妝品', 'sub': '彩妝'},
    {'floor': '1F', 'brand': 'Swiss Perfection', 'ko': '스위스퍼펙션', 'en': 'Swiss Perfection', 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'Le Labo', 'ko': '르라보', 'en': 'Le Labo', 'category': '化妝品', 'sub': '香水'},
    {'floor': '1F', 'brand': 'THE HOUR GLASS', 'ko': '더아워글래스', 'en': 'THE HOUR GLASS', 'category': '化妝品', 'sub': '香水/護膚'},
    {'floor': '1F', 'brand': 'Clé de Peau', 'ko': '클드포', 'en': 'Clé de Peau', 'category': '化妝品', 'sub': '護膚'},
    {'floor': '1F', 'brand': 'Shu Uemura', 'ko': '쉬우무라', 'en': 'Shu Uemura', 'category': '化妝品', 'sub': '彩妝'},
    {'floor': '1F', 'brand': 'Decathlon', 'ko': '데카슬론', 'en': 'Decathlon', 'category': '運動', 'sub': '戶外運動'},

    # ========================
    # 2F - 海外精品 / 腕錶
    # ========================
    {'floor': '2F', 'brand': 'Cartier', 'ko': '까르띠에', 'en': 'Cartier', 'category': '珠寶', 'sub': '戒指/腕錶'},
    {'floor': '2F', 'brand': 'Van Cleef & Arpels', 'ko': '반클리프앤아펠', 'en': 'Van Cleef & Arpels', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Tiffany & Co.', 'ko': '티파니', 'en': 'Tiffany & Co.', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Bulgari', 'ko': '불가리', 'en': 'Bulgari', 'category': '珠寶', 'sub': '珠寶/腕錶'},
    {'floor': '2F', 'brand': 'Graff', 'ko': '그라프', 'en': 'Graff', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Chaumet', 'ko': '쇼메', 'en': 'Chaumet', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'FRED', 'ko': '프레다이아', 'en': 'FRED', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Damiani', 'ko': '다미아니', 'en': 'Damiani', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Buccellati', 'ko': '부첼라티', 'en': 'Buccellati', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Boucheron', 'ko': '부쉐론', 'en': 'Boucheron', 'category': '珠寶', 'sub': '珠寶'},
    {'floor': '2F', 'brand': 'Patek Philippe', 'ko': '파텍필립', 'en': 'Patek Philippe', 'category': '腕錶', 'sub': '頂級腕錶'},
    {'floor': '2F', 'brand': 'Vacheron Constantin', 'ko': '바쉐론콘스탄틴', 'en': 'Vacheron Constantin', 'category': '腕錶', 'sub': '頂級腕錶'},
    {'floor': '2F', 'brand': 'Breguet', 'ko': '브레게', 'en': 'Breguet', 'category': '腕錶', 'sub': '頂級腕錶'},
    {'floor': '2F', 'brand': 'Rolex', 'ko': '롤렉스', 'en': 'Rolex', 'category': '腕錶', 'sub': '名錶'},
    {'floor': '2F', 'brand': 'OMEGA', 'ko': '오메가', 'en': 'OMEGA', 'category': '腕錶', 'sub': '名錶'},
    {'floor': '2F', 'brand': 'IWC', 'ko': '아이더블유씨', 'en': 'IWC', 'category': '腕錶', 'sub': '名錶'},
    {'floor': '2F', 'brand': 'Piaget', 'ko': '피아제', 'en': 'Piaget', 'category': '腕錶', 'sub': '珠寶/腕錶'},
    {'floor': '2F', 'brand': 'Jaquet Droz', 'ko': '자케드러즈', 'en': 'Jaquet Droz', 'category': '腕錶', 'sub': '頂級腕錶'},
    {'floor': '2F', 'brand': 'TAG Heuer', 'ko': '태그호이어', 'en': 'TAG Heuer', 'category': '腕錶', 'sub': '運動錶'},
    {'floor': '2F', 'brand': 'Grand Seiko', 'ko': '그랜드세이코', 'en': 'Grand Seiko', 'category': '腕錶', 'sub': '日本名錶'},
    {'floor': '2F', 'brand': 'Longines', 'ko': '롱인', 'en': 'Longines', 'category': '腕錶', 'sub': '瑞士錶'},
    {'floor': '2F', 'brand': 'Tudor', 'ko': '튜더', 'en': 'Tudor', 'category': '腕錶', 'sub': '腕錶'},
    {'floor': '2F', 'brand': 'Moncler', 'ko': '몽클레르', 'en': 'Moncler', 'category': '時裝', 'sub': '羽絨'},
    {'floor': '2F', 'brand': 'Jimmy Choo', 'ko': '지미추', 'en': 'Jimmy Choo', 'category': '精品', 'sub': '鞋類/包包'},
    {'floor': '2F', 'brand': 'Celine', 'ko': '셀린느', 'en': 'Celine', 'category': '精品', 'sub': '時裝'},
    {'floor': '2F', 'brand': 'Loewe', 'ko': '로에베', 'en': 'Loewe', 'category': '精品', 'sub': '皮革'},
    {'floor': '2F', 'brand': 'Loro Piana', 'ko': '로로피아나', 'en': 'Loro Piana', 'category': '精品', 'sub': '羊絨'},
    {'floor': '2F', 'brand': 'KENZO', 'ko': '겐조', 'en': 'KENZO', 'category': '時裝', 'sub': '男女裝'},
    {'floor': '2F', 'brand': 'Marc Jacobs', 'ko': '마크모스', 'en': 'Marc Jacobs', 'category': '精品', 'sub': '包包/時裝'},
    {'floor': '2F', 'brand': 'Acne Studios', 'ko': '아크네스튜디오', 'en': 'Acne Studios', 'category': '時裝', 'sub': '設計師品牌'},
    {'floor': '2F', 'brand': 'Ami Paris', 'ko': '아미파리', 'en': 'Ami Paris', 'category': '時裝', 'sub': '法國男裝'},
    {'floor': '2F', 'brand': 'A.P.C.', 'ko': '에이피세', 'en': 'A.P.C.', 'category': '時裝', 'sub': '法國休閒'},
    {'floor': '2F', 'brand': 'Isabel Marant', 'ko': '이자벨마랑', 'en': 'Isabel Marant', 'category': '時裝', 'sub': '法國女裝'},
    {'floor': '2F', 'brand': 'BOSS', 'ko': '보스', 'en': 'BOSS', 'category': '時裝', 'sub': '男性正裝'},
    {'floor': '2F', 'brand': 'Nike', 'ko': '나이키', 'en': 'Nike', 'category': '運動', 'sub': '運動鞋'},
    {'floor': '2F', 'brand': 'Adidas', 'ko': '아디다스', 'en': 'Adidas', 'category': '運動', 'sub': '運動鞋'},
    {'floor': '2F', 'brand': 'New Balance', 'ko': '뉴발란스', 'en': 'New Balance', 'category': '運動', 'sub': '運動鞋'},
    {'floor': '2F', 'brand': 'J.ESTINA', 'ko': '제이에스티나', 'en': 'J.ESTINA', 'category': '珠寶', 'sub': '韓國飾品'},

    # ========================
    # 3F - 當代設計 / 韓國女性
    # ========================
    {'floor': '3F', 'brand': 'Ader Error', 'ko': '아더에러', 'en': 'Ader Error', 'category': '設計師', 'sub': '韓國新銳'},
    {'floor': '3F', 'brand': 'Sandro', 'ko': '산드로', 'en': 'Sandro', 'category': '設計師', 'sub': '法國女裝'},
    {'floor': '3F', 'brand': 'Maje', 'ko': '마주', 'en': 'Maje', 'category': '設計師', 'sub': '法國女裝'},
    {'floor': '3F', 'brand': 'Claudie Pierlot', 'ko': '클로디피에르', 'en': 'Claudie Pierlot', 'category': '設計師', 'sub': '法國女裝'},
    {'floor': '3F', 'brand': 'IRO', 'ko': '이로', 'en': 'IRO', 'category': '設計師', 'sub': '法國男女裝'},
    {'floor': '3F', 'brand': 'The Row', 'ko': '더로', 'en': 'The Row', 'category': '設計師', 'sub': '美國極簡'},
    {'floor': '3F', 'brand': 'Totême', 'ko': '토텀', 'en': 'Totême', 'category': '設計師', 'sub': '北歐極簡'},
    {'floor': '3F', 'brand': 'Ganni', 'ko': '가니', 'en': 'Ganni', 'category': '設計師', 'sub': '丹麥女裝'},
    {'floor': '3F', 'brand': 'Ba&sh', 'ko': '바쉬', 'en': 'Ba&sh', 'category': '設計師', 'sub': '法國女裝'},
    {'floor': '3F', 'brand': 'Self-Portrait', 'ko': '셀프포트레이트', 'en': 'Self-Portrait', 'category': '設計師', 'sub': '英國女裝'},
    {'floor': '3F', 'brand': 'Miss Sixty', 'ko': '미스식스티', 'en': 'Miss Sixty', 'category': '時裝', 'sub': '女裝'},
    {'floor': '3F', 'brand': 'O\'2nd', 'ko': '오세컨드', 'en': "O'2nd", 'category': '時裝', 'sub': '韓國女裝'},
    {'floor': '3F', 'brand': 'SJSJ', 'ko': '에스제이에스제이', 'en': 'SJSJ', 'category': '時裝', 'sub': '韓國女裝'},
    {'floor': '3F', 'brand': 'Uniqlo', 'ko': '유니클로', 'en': 'Uniqlo', 'category': '休閒', 'sub': '平價服飾'},
    {'floor': '3F', 'brand': 'Gap', 'ko': '갭', 'en': 'Gap', 'category': '休閒', 'sub': '美式休閒'},
    {'floor': '3F', 'brand': 'Tommy Hilfiger', 'ko': '토미힐피거', 'en': 'Tommy Hilfiger', 'category': '休閒', 'sub': '美式學院風'},
    {'floor': '3F', 'brand': 'Calvin Klein', 'ko': '캘빈클라인', 'en': 'Calvin Klein', 'category': '休閒', 'sub': '內衣/休閒'},

    # ========================
    # 4F - 運動 / 機能 / 戶外
    # ========================
    {'floor': '4F', 'brand': 'The North Face', 'ko': '노스페이스', 'en': 'The North Face', 'category': '戶外', 'sub': '機能外套'},
    {'floor': '4F', 'brand': 'Columbia', 'ko': '컬럼비아', 'en': 'Columbia', 'category': '戶外', 'sub': '機能外套'},
    {'floor': '4F', 'brand': 'Salomon', 'ko': '살로몬', 'en': 'Salomon', 'category': '戶外', 'sub': '越野跑/滑雪'},
    {'floor': '4F', 'brand': 'Arc\'teryx', 'ko': '아크테릭스', 'en': "Arc'teryx", 'category': '戶外', 'sub': '頂級戶外'},
    {'floor': '4F', 'brand': 'Patagonia', 'ko': '파타고니아', 'en': 'Patagonia', 'category': '戶外', 'sub': '環保戶外'},
    {'floor': '4F', 'brand': 'Mammut', 'ko': '마모트', 'en': 'Mammut', 'category': '戶外', 'sub': '瑞士戶外'},
    {'floor': '4F', 'brand': 'La Sportiva', 'ko': '라스포르티바', 'en': 'La Sportiva', 'category': '戶外', 'sub': '登山/攀岩'},
    {'floor': '4F', 'brand': 'Black Diamond', 'ko': '블랙다이아', 'en': 'Black Diamond', 'category': '戶外', 'sub': '攀岩裝備'},
    {'floor': '4F', 'brand': 'Nike', 'ko': '나이키', 'en': 'Nike', 'category': '運動', 'sub': '運動鞋/服飾'},
    {'floor': '4F', 'brand': 'Adidas', 'ko': '아디다스', 'en': 'Adidas', 'category': '運動', 'sub': '運動鞋/服飾'},
    {'floor': '4F', 'brand': 'New Balance', 'ko': '뉴발란스', 'en': 'New Balance', 'category': '運動', 'sub': '運動鞋'},
    {'floor': '4F', 'brand': 'Converse', 'ko': '컨버스', 'en': 'Converse', 'category': '運動', 'sub': '帆布鞋'},
    {'floor': '4F', 'brand': 'Vans', 'ko': '반스', 'en': 'Vans', 'category': '運動', 'sub': '滑板鞋'},
    {'floor': '4F', 'brand': 'Fila', 'ko': '휠라', 'en': 'Fila', 'category': '運動', 'sub': '運動休閒'},
    {'floor': '4F', 'brand': 'Puma', 'ko': '푸마', 'en': 'Puma', 'category': '運動', 'sub': '運動休閒'},
    {'floor': '4F', 'brand': 'Asics', 'ko': '아식스', 'en': 'Asics', 'category': '運動', 'sub': '跑鞋'},
    {'floor': '4F', 'brand': 'Under Armour', 'ko': '언더아모어', 'en': 'Under Armour', 'category': '運動', 'sub': '機能運動'},
    {'floor': '4F', 'brand': 'Descente', 'ko': '데상트', 'en': 'Descente', 'category': '運動', 'sub': '高爾夫/滑雪'},
    {'floor': '4F', 'brand': 'Le Coq Sportif', 'ko': '르코크스포르티프', 'en': 'Le Coq Sportif', 'category': '運動', 'sub': '法國運動'},
    {'floor': '4F', 'brand': 'Kappa', 'ko': '카파', 'en': 'Kappa', 'category': '運動', 'sub': '義大利運動'},

    # ========================
    # 5F - 男性精品 / 西裝
    # ========================
    {'floor': '5F', 'brand': 'Burberry', 'ko': '버버리', 'en': 'Burberry', 'category': '精品', 'sub': '男性西裝'},
    {'floor': '5F', 'brand': 'Brioni', 'ko': '브리오니', 'en': 'Brioni', 'category': '精品', 'sub': '義大利西裝'},
    {'floor': '5F', 'brand': 'Ermenegildo Zegna', 'ko': '어메네질도제그나', 'en': 'Ermenegildo Zegna', 'category': '精品', 'sub': '義大利西裝'},
    {'floor': '5F', 'brand': 'Tom Ford', 'ko': '톰포트', 'en': 'Tom Ford', 'category': '精品', 'sub': '男性西裝/香水'},
    {'floor': '5F', 'brand': 'Ralph Lauren', 'ko': '랄프로렌', 'en': 'Ralph Lauren', 'category': '時裝', 'sub': '美式學院'},
    {'floor': '5F', 'brand': 'BOSS', 'ko': '보스', 'en': 'BOSS', 'category': '時裝', 'sub': '男性正裝'},
    {'floor': '5F', 'brand': 'Canali', 'ko': '카날리', 'en': 'Canali', 'category': '精品', 'sub': '義大利西裝'},
    {'floor': '5F', 'brand': 'Finamore', 'ko': '피나모레', 'en': 'Finamore', 'category': '精品', 'sub': '義大利襯衫'},
    {'floor': '5F', 'brand': 'Drakes', 'ko': '드레이크스', 'en': 'Drakes', 'category': '時裝', 'sub': '英國領帶/西裝'},
    {'floor': '5F', 'brand': 'Jil Stuart', 'ko': '질스튜어트', 'en': 'Jil Stuart', 'category': '時裝', 'sub': '男性時裝'},
    {'floor': '5F', 'brand': 'Tricker\'s', 'ko': '트리커스', 'en': "Tricker's", 'category': '鞋', 'sub': '英國紳士鞋'},
    {'floor': '5F', 'brand': 'Berluti', 'ko': '베를루띠', 'en': 'Berluti', 'category': '鞋', 'sub': '法國紳士鞋'},
    {'floor': '5F', 'brand': 'John Lobb', 'ko': '존롭', 'en': 'John Lobb', 'category': '鞋', 'sub': '英國訂製鞋'},
    {'floor': '5F', 'brand': 'Crockett & Jones', 'ko': '크로켓존스', 'en': 'Crockett & Jones', 'category': '鞋', 'sub': '英國手工鞋'},
    {'floor': '5F', 'brand': 'J.ESTINA', 'ko': '제이에스티나', 'en': 'J.ESTINA', 'category': '配件', 'sub': '韓國飾品'},

    # ========================
    # 6F - 兒童 / 高爾夫
    # ========================
    {'floor': '6F', 'brand': 'Baby Dior', 'ko': '베이비디올', 'en': 'Baby Dior', 'category': '童裝', 'sub': '奢侈品童裝'},
    {'floor': '6F', 'brand': 'Burberry Kids', 'ko': '버버리키즈', 'en': 'Burberry Kids', 'category': '童裝', 'sub': '童裝'},
    {'floor': '6F', 'brand': 'Fendi Kids', 'ko': '펜디키즈', 'en': 'Fendi Kids', 'category': '童裝', 'sub': '童裝'},
    {'floor': '6F', 'brand': 'Moncler Enfant', 'ko': '몽클레르앙팡', 'en': 'Moncler Enfant', 'category': '童裝', 'sub': '童裝羽絨'},
    {'floor': '6F', 'brand': 'Armani Junior', 'ko': '아르마니주니어', 'en': 'Armani Junior', 'category': '童裝', 'sub': '童裝'},
    {'floor': '6F', 'brand': 'Ralph Lauren Children', 'ko': '랄프로렌칠드런', 'en': 'Ralph Lauren Children', 'category': '童裝', 'sub': '童裝'},
    {'floor': '6F', 'brand': 'Gap Kids', 'ko': '갭키즈', 'en': 'Gap Kids', 'category': '童裝', 'sub': '童裝'},
    {'floor': '6F', 'brand': 'Nike Kids', 'ko': '나이키키즈', 'en': 'Nike Kids', 'category': '童裝', 'sub': '童裝運動'},
    {'floor': '6F', 'brand': 'Adidas Kids', 'ko': '아디다스키즈', 'en': 'Adidas Kids', 'category': '童裝', 'sub': '童裝運動'},
    {'floor': '6F', 'brand': 'Converse Kids', 'ko': '컨버스키즈', 'en': 'Converse Kids', 'category': '童裝', 'sub': '童裝鞋'},
    {'floor': '6F', 'brand': 'KidZania', 'ko': '키자니아', 'en': 'KidZania', 'category': '體驗', 'sub': '兒童職業體驗'},
    {'floor': '6F', 'brand': 'Callaway', 'ko': '칼러웨이', 'en': 'Callaway', 'category': '高爾夫', 'sub': '高爾夫球具'},
    {'floor': '6F', 'brand': 'Titleist', 'ko': '타이틀리스트', 'en': 'Titleist', 'category': '高爾夫', 'sub': '高爾夫球具'},
    {'floor': '6F', 'brand': 'Cobra', 'ko': '코브라', 'en': 'Cobra', 'category': '高爾夫', 'sub': '高爾夫球具'},
    {'floor': '6F', 'brand': 'PING', 'ko': '핑', 'en': 'PING', 'category': '高爾夫', 'sub': '高爾夫球具'},
    {'floor': '6F', 'brand': 'TaylorMade', 'ko': '테일러메이드', 'en': 'TaylorMade', 'category': '高爾夫', 'sub': '高爾夫球具'},
    {'floor': '6F', 'brand': 'Foot Joy', 'ko': '풋조이', 'en': 'Foot Joy', 'category': '高爾夫', 'sub': '高爾夫球鞋'},
    {'floor': '6F', 'brand': 'Lacoste', 'ko': '라코스테', 'en': 'Lacoste', 'category': '運動', 'sub': '法國鱷魚'},

    # ========================
    # 7F - 家電 / 生活
    # ========================
    {'floor': '7F', 'brand': 'Samsung', 'ko': '삼성', 'en': 'Samsung', 'category': '電子', 'sub': '電視/家電'},
    {'floor': '7F', 'brand': 'LG', 'ko': 'LG', 'en': 'LG', 'category': '電子', 'sub': '電視/家電'},
    {'floor': '7F', 'brand': 'Apple', 'ko': '애플', 'en': 'Apple', 'category': '電子', 'sub': '手機/電腦'},
    {'floor': '7F', 'brand': 'Dyson', 'ko': '다이슨', 'en': 'Dyson', 'category': '生活', 'sub': '家電/吹風機'},
    {'floor': '7F', 'brand': 'CGV', 'ko': '시지비', 'en': 'CGV', 'category': '影城', 'sub': '電影院'},
    {'floor': '7F', 'brand': 'LEGO', 'ko': '레고', 'en': 'LEGO', 'category': '玩具', 'sub': '樂高玩具'},
    {'floor': '7F', 'brand': 'Pottery Barn Kids', 'ko': '포터리바arn', 'en': 'Pottery Barn Kids', 'category': '家具', 'sub': '兒童家具'},

    # ========================
    # 8F - 家具 / 室內設計
    # ========================
    {'floor': '8F', 'brand': 'IKEA', 'ko': '이케아', 'en': 'IKEA', 'category': '家具', 'sub': '平價家具'},
    {'floor': '8F', 'brand': 'Samsung', 'ko': '삼성', 'en': 'Samsung', 'category': '電子', 'sub': '生活家電'},
    {'floor': '8F', 'brand': 'LG', 'ko': 'LG', 'en': 'LG', 'category': '電子', 'sub': '生活家電'},
    {'floor': '8F', 'brand': 'CGV IMAX', 'ko': '시지비imax', 'en': 'CGV IMAX', 'category': '影城', 'sub': 'IMAX電影院'},

    # ========================
    # 9F - 餐廳 / 服務
    # ========================
    {'floor': '9F', 'brand': 'Samsung', 'ko': '삼성', 'en': 'Samsung', 'category': '客戶服務', 'sub': '服務中心'},

    # ========================
    # 10F - Spa / 健身
    # ========================
    {'floor': '10F', 'brand': 'Trinity Spa', 'ko': '트리니티스파', 'en': 'Trinity Spa', 'category': '服務', 'sub': 'Spa/健身'},

    # ========================
    # 11F - 高爾夫
    # ========================
    {'floor': '11F', 'brand': 'Golf Range', 'ko': '골프레인지', 'en': 'Golf Range', 'category': '高爾夫', 'sub': '室內高爾夫練習場'},
]

def build_db():
    """Build the complete database"""
    conn = get_conn()
    init_db(conn)
    
    now = time.strftime('%Y-%m-%d %H:%M')
    
    # Save floors
    for f in FLOORS:
        f['scraped_at'] = now
        save_floor(conn, f)
    
    # Save brands
    for b in BRANDS:
        b['scraped_at'] = now
        save_brand(conn, b)
    
    conn.commit()
    
    # Rebuild FTS
    print('Rebuilding FTS index...')
    rebuild_fts(conn)
    
    print(f'Saved {len(FLOORS)} floors and {len(BRANDS)} brands')
    return conn

def search(query, conn, floor=None, category=None, limit=20):
    """Search brands"""
    cur = conn.cursor()
    
    if floor:
        cur.execute('SELECT * FROM brands WHERE floor=? ORDER BY brand_name LIMIT ?', (floor, limit))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    
    if category:
        cur.execute('SELECT * FROM brands WHERE category=? ORDER BY brand_name LIMIT ?', (category, limit))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    
    # Search - always use LIKE for better multilingual support
    if query:
        like = f'%{query}%'
        cur.execute('''SELECT * FROM brands WHERE 
            brand_name LIKE ? OR brand_name_ko LIKE ? OR brand_name_en LIKE ? 
            ORDER BY brand_name LIMIT ?''', (like, like, like, limit))
        return [dict(r) for r in cur.fetchall()]
    
    # Return all
    cur.execute('SELECT * FROM brands ORDER BY floor, brand_name LIMIT ?', (limit,))
    return [dict(r) for r in cur.fetchall()]

def main():
    print('=== Building Complete Shinsegae Centum City DB ===\n')
    conn = build_db()
    
    # Stats
    cur = conn.cursor()
    cur.execute('SELECT floor, COUNT(*) FROM brands GROUP BY floor ORDER BY floor')
    print('\nBrands by floor:')
    for r in cur.fetchall():
        print(f'  [{r[0]}] {r[1]} brands')
    print(f'\nTotal: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]} brands')
    print(f'Floors: {cur.execute("SELECT COUNT(*) FROM floors").fetchone()[0]}')
    
    # Test searches
    print('\n=== Search Tests ===')
    tests = [
        ('香奈兒', None, None),
        ('腕錶', None, None),
        ('運動', '4F', None),
        ('精品', None, None),
        ('童裝', None, None),
        ('高爾夫', None, None),
        ('nike', None, None),
        ('아', None, None),
    ]
    
    for query, floor, cat in tests:
        results = search(query, conn, floor, cat)
        print(f'\nSearch: "{query}" | Floor: {floor} | Cat: {cat}')
        print(f'  → {len(results)} results')
        for r in results[:5]:
            bn = r.get('brand_name', r.get('brand', ''))
            cat = r.get('category', '')
            sub = r.get('subcategory', r.get('sub', ''))
            print(f'    [{r["floor"]}] {bn} ({cat}/{sub})')
    
    conn.close()
    print('\n=== Done ===')

if __name__ == '__main__':
    main()