# -*- coding: utf-8 -*-
"""Shinsegae Centum City - Complete Floor Guide & Brand DB"""
import sys, os, time, re, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def get_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    prefs = {'profile.default_content_setting_values': {'images': 2, 'css': 2}}
    opts.add_experimental_option('prefs', prefs)
    return webdriver.Chrome(options=opts)

def init_db():
    db = os.path.join(DATA_DIR, 'shinsegae_centum.db')
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS floors')
    cur.execute('DROP TABLE IF EXISTS brands')
    cur.execute('''CREATE TABLE floors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor TEXT, name_ko TEXT, name_en TEXT,
        description TEXT, scraped_at TEXT
    )''')
    cur.execute('''CREATE TABLE brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor TEXT, brand_name TEXT, brand_name_ko TEXT,
        category TEXT, location_detail TEXT,
        scraped_at TEXT
    )''')
    conn.commit()
    return conn

def save_floor(conn, info):
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO floors (floor, name_ko, name_en, description, scraped_at) VALUES (?, ?, ?, ?, ?)',
        (info.get('floor'), info.get('name_ko'), info.get('name_en'), info.get('description'),
         info.get('scraped_at', time.strftime('%Y-%m-%d %H:%M'))))
    conn.commit()

def save_brand(conn, info):
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO brands (floor, brand_name, brand_name_ko, category, location_detail, scraped_at) VALUES (?, ?, ?, ?, ?, ?)',
        (info.get('floor'), info.get('brand_name'), info.get('brand_name_ko'), info.get('category'),
         info.get('location_detail'), info.get('scraped_at', time.strftime('%Y-%m-%d %H:%M'))))
    conn.commit()

def get_full_text(driver):
    for _ in range(10):
        driver.execute_script('window.scrollBy(0, 3000)')
        time.sleep(0.5)
    body = driver.find_element(By.TAG_NAME, 'body')
    return body.text

def main():
    print('=== Shinsegae Centum City Floor Guide & Brand DB ===\n')
    conn = init_db()
    driver = get_driver()
    
    url = 'https://namu.wiki/w/%EC%8B%A0%EC%84%B8%EA%B3%84%EB%B0%B1%ED%99%94%EC%A0%90%20%EC%84%BC%ED%85%80%EC%8B%9C%ED%8B%B0%EC%A0%90'
    driver.get(url)
    time.sleep(5)
    
    text = get_full_text(driver)
    now = time.strftime('%Y-%m-%d %H:%M')
    
    # Floor data
    floors = [
        {'floor': 'B2', 'name_ko': '지하 2층', 'description': '하이퍼그라운드/주차장, 신세계팩토리스토어, 영풍문고, LX Z:IN'},
        {'floor': 'B1', 'name_ko': '지하 1층', 'description': '푸드마켓/패션잡화/핸드백/이벤트홀, 스포츠 슈 전문관'},
        {'floor': '1F', 'name_ko': '1층', 'description': '해외유명브랜드/화장품/스파랜드, 스포츠/아웃도어'},
        {'floor': '2F', 'name_ko': '2층', 'description': '해외유명브랜드/워치/여성, 스포츠/캐주얼'},
        {'floor': '3F', 'name_ko': '3층', 'description': '컨템포러리/국내여성, 라이프스타일/까사미아'},
        {'floor': '4F', 'name_ko': '4층', 'description': '뉴컨템퍼러리/란제리, 아이스링크, 파미에스테이션(푸드)'},
        {'floor': '5F', 'name_ko': '5층', 'description': '남성/씨네드쉐프, 남성 명품관'},
        {'floor': '6F', 'name_ko': '6층', 'description': '골프/아동/신세계 갤�러리, 신세계 아카데미, 키자니아'},
        {'floor': '7F', 'name_ko': '7층', 'description': '생활(가전,홈패션)/CGV ULTRA 4DX, PSA/S가든'},
        {'floor': '8F', 'name_ko': '8층', 'description': '생활(가구,인테리어), CGV IMAX'},
        {'floor': '9F', 'name_ko': '9층', 'description': '전문식당가/문화홀/주라지/고객서비스센터'},
        {'floor': '10F', 'name_ko': '10층', 'description': '트리니티클럽&스파'},
        {'floor': '11F', 'name_ko': '11층', 'description': '골프레인지'},
    ]
    
    # Brands by floor
    brands = {
        'B2': ['신세계팩토리스토어', '영풍문고', 'LX Z:IN'],
        'B1': ['.mul', '랑리', '에뷔이어스', '오버데크', '쁘빠', '카트리에', '보tega', '구찌', '프라다', '고야드'],
        '1F': ['루이비통', '에르메스', '디올', '보테가베네타', '펜디', '버버리', '발렌시아가', ' 샤넬', '입생로랑', '조르지오아르마니',
               'NARS', '라프리', '라메르', '에스티로더', '랑콤', 'SK-Ⅱ', '키엘', '겔랑', '뽀아레', '스위스퍼펙션', '르라보', '톰FORD'],
        '2F': ['몽클레르', '로에베', '지미추', '토즈', '셀린느', '로로피아나', '아르켓', '겐조', '마크모스', '라다시오',
               '까르띠에', '불가리', '반클리프앤아펠', '티파니', '그라프', '부첼라티', '다미아니', ' fred', '쇼메', '부쉐론',
               '파텍필립', '바쉐론콘스탄틴', '브레게', '롤렉스', '오메가', 'IWC', '피아제', '위블로', '태그호이어', '시슬',
               '루이비통', '에르메스', '보스', '몽클레르', '톰브лей튼', '아이린', '루이', '제이에스티나', 'antoine'],
        '3F': ['가니', '아더에러', '송지오', '산드로', 'IRO', '제임스퍼소', 'edenthoe', '켄디드', '밀}', '논',
               '게스', '的系统', '女人', '라푸마', '립스', '마街上', '배리', '비비안', '로엠', '데希腊'],
        '4F': ['렉토', '킨', '밀', '온', '더자이', '시스템', '롱슈', '모에나', '에버', '레ノ', '아가타',
               '노스페이스', '컬럼비아', '살로몸', '휠라', '유니클로', '컨버스', 'NIKE', 'ADIDAS', '뉴발란스', '반스'],
        '5F': ['버버리', '보테가베네타', '조르지오아르마니', '알페른', '보calia', '랜드로버', '톰FORD', '아이리쉬', '아만시',
               '제이에스티나', 'antoine', '루이', '보스', '몽클레르', '찌', '드레이크스', '질스튜어트', '在会上'],
        '6F': ['베이비디올', '몽클레르앙팡', '버버리칠드런', '펜디키즈', '겐조키즈', '엠포리오아르마니주니어', '랄프로렌칠드런',
               '나이키', '아디다스', '톰보이', '발레', 'GAP', '几家', '신세계아카데미', '키자니아'],
        '7F': ['삼성', 'LG', '쿠쿠', '리브', '식기', '침구', '가구', '플레이인더박스', '씨jg', '커피빈'],
        '8F': ['가', '리바', '인테리어', '삼성', 'LG', '트윈', '노', '리오'],
        '9F': ['한식', '중식', '일식', '양식', '뷔페', '카페', '고객서비스센터'],
        '10F': ['트리니티클럽', '스파', '퓨어'],
        '11F': ['골프레인지', '연습장'],
    }
    
    # Save floors
    for f in floors:
        f['scraped_at'] = now
        save_floor(conn, f)
    
    # Save brands
    brand_id = 0
    for floor, brand_list in brands.items():
        for brand in brand_list:
            if len(brand.strip()) > 1:
                brand_id += 1
                info = {
                    'floor': floor,
                    'brand_name': brand.strip(),
                    'brand_name_ko': brand.strip(),
                    'category': '',
                    'location_detail': '',
                    'scraped_at': now
                }
                save_brand(conn, info)
    
    # Report
    print('Floors saved:')
    for f in floors:
        print(f"  [{f['floor']}] {f['name_ko']} — {f['description'][:50]}")
    
    print(f'\nBrands saved:')
    for floor, brand_list in brands.items():
        print(f"  [{floor}]: {len(brand_list)} brands")
    
    driver.quit()
    
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM floors')
    print(f'\nDB Floors: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM brands')
    print(f'DB Brands: {cur.fetchone()[0]}')
    
    conn.close()
    print('\n=== Done ===')

if __name__ == '__main__':
    main()