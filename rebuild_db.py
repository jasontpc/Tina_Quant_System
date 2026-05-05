# -*- coding: utf-8 -*-
"""Rebuild Shinsegae Centum City DB with correct column mapping"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = os.path.join(DATA_DIR, 'shinsegae_centum.db')

BRANDS = [
    # ======================== B2 ========================
    {'floor': 'B2', 'brand_name': '新世界 Factory Store', 'brand_name_ko': '신세계팩토리스토어', 'brand_name_en': 'Shinsegae Factory Store', 'category': '生活', 'subcategory': '工廠直營店'},
    {'floor': 'B2', 'brand_name': '永豐文庫', 'brand_name_ko': '영풍문고', 'brand_name_en': 'Youngpoong Bookstore', 'category': '文化', 'subcategory': '書店'},
    {'floor': 'B2', 'brand_name': 'LX Z:IN', 'brand_name_ko': 'LX Z:IN', 'brand_name_en': 'LX Z:IN', 'category': '生活', 'subcategory': '室內建材'},
    # ======================== B1 ========================
    {'floor': 'B1', 'brand_name': 'Bottega Veneta', 'brand_name_ko': '보테가베네타', 'brand_name_en': 'Bottega Veneta', 'category': '精品', 'subcategory': '皮革'},
    {'floor': 'B1', 'brand_name': 'Goyard', 'brand_name_ko': '고야드', 'brand_name_en': 'Goyard', 'category': '精品', 'subcategory': '行李箱'},
    {'floor': 'B1', 'brand_name': 'Prada', 'brand_name_ko': '프라다', 'brand_name_en': 'Prada', 'category': '精品', 'subcategory': '時裝'},
    {'floor': 'B1', 'brand_name': 'Moynat', 'brand_name_ko': '모이나', 'brand_name_en': 'Moynat', 'category': '精品', 'subcategory': '行李箱'},
    {'floor': 'B1', 'brand_name': 'Mul', 'brand_name_ko': '뮬', 'brand_name_en': 'Mul', 'category': '精品', 'subcategory': '皮具'},
    {'floor': 'B1', 'brand_name': 'Loro Piana', 'brand_name_ko': '로로피아나', 'brand_name_en': 'Loro Piana', 'category': '精品', 'subcategory': '羊絨'},
    {'floor': 'B1', 'brand_name': 'Moorer', 'brand_name_ko': '무라', 'brand_name_en': 'Moorer', 'category': '精品', 'subcategory': '羽絨'},
    {'floor': 'B1', 'brand_name': 'Parosh', 'brand_name_ko': '파로쉬', 'brand_name_en': 'Parosh', 'category': '時裝', 'subcategory': '女裝'},
    {'floor': 'B1', 'brand_name': 'Covernat', 'brand_name_ko': '커버낫', 'brand_name_en': 'Covernat', 'category': '運動', 'subcategory': '鞋類'},
    {'floor': 'B1', 'brand_name': 'ABC-MART', 'brand_name_ko': 'ABC마트', 'brand_name_en': 'ABC-MART', 'category': '運動', 'subcategory': '鞋類專門店'},
    {'floor': 'B1', 'brand_name': 'New Balance', 'brand_name_ko': '뉴발란스', 'brand_name_en': 'New Balance', 'category': '運動', 'subcategory': '鞋類'},
    {'floor': 'B1', 'brand_name': 'Hummel', 'brand_name_ko': '훔멜', 'brand_name_en': 'Hummel', 'category': '運動', 'subcategory': '運動休閒'},
    # ======================== 1F ========================
    {'floor': '1F', 'brand_name': 'Louis Vuitton', 'brand_name_ko': '루이비통', 'brand_name_en': 'Louis Vuitton', 'category': '精品', 'subcategory': '時裝/行李箱'},
    {'floor': '1F', 'brand_name': 'Hermès', 'brand_name_ko': '에르메스', 'brand_name_en': 'Hermès', 'category': '精品', 'subcategory': '時裝/皮革'},
    {'floor': '1F', 'brand_name': 'Dior', 'brand_name_ko': '디올', 'brand_name_en': 'Dior', 'category': '精品', 'subcategory': '時裝/化妝品'},
    {'floor': '1F', 'brand_name': 'Chanel', 'brand_name_ko': '샤넬', 'brand_name_en': 'Chanel', 'category': '精品', 'subcategory': '時裝/化妝品'},
    {'floor': '1F', 'brand_name': 'Balenciaga', 'brand_name_ko': '발렌시아가', 'brand_name_en': 'Balenciaga', 'category': '精品', 'subcategory': '時裝'},
    {'floor': '1F', 'brand_name': 'Gucci', 'brand_name_ko': '구찌', 'brand_name_en': 'Gucci', 'category': '精品', 'subcategory': '時裝/皮革'},
    {'floor': '1F', 'brand_name': 'Fendi', 'brand_name_ko': '펜디', 'brand_name_en': 'Fendi', 'category': '精品', 'subcategory': '時裝/皮革'},
    {'floor': '1F', 'brand_name': 'Burberry', 'brand_name_ko': '버버리', 'brand_name_en': 'Burberry', 'category': '精品', 'subcategory': '時裝'},
    {'floor': '1F', 'brand_name': 'Yves Saint Laurent', 'brand_name_ko': '입생로랑', 'brand_name_en': 'Yves Saint Laurent', 'category': '精品', 'subcategory': '化妝品'},
    {'floor': '1F', 'brand_name': 'Giorgio Armani', 'brand_name_ko': '조르지오아르마니', 'brand_name_en': 'Giorgio Armani', 'category': '精品', 'subcategory': '化妝品'},
    {'floor': '1F', 'brand_name': 'Loewe', 'brand_name_ko': '로에베', 'brand_name_en': 'Loewe', 'category': '精品', 'subcategory': '皮革'},
    {'floor': '1F', 'brand_name': 'Tod\'s', 'brand_name_ko': '토즈', 'brand_name_en': "Tod's", 'category': '精品', 'subcategory': '鞋類/皮革'},
    {'floor': '1F', 'brand_name': 'Tom Ford', 'brand_name_ko': '톰포트', 'brand_name_en': 'Tom Ford', 'category': '化妝品', 'subcategory': '香水/護膚'},
    {'floor': '1F', 'brand_name': 'NARS', 'brand_name_ko': '날스', 'brand_name_en': 'NARS', 'category': '化妝品', 'subcategory': '彩妝'},
    {'floor': '1F', 'brand_name': 'SK-II', 'brand_name_ko': '에스케이투', 'brand_name_en': 'SK-II', 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'La Mer', 'brand_name_ko': '라메르', 'brand_name_en': 'La Mer', 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'La Prairie', 'brand_name_ko': '라프라이', 'brand_name_en': 'La Prairie', 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'Estée Lauder', 'brand_name_ko': '에스티로더', 'brand_name_en': 'Estée Lauder', 'category': '化妝品', 'subcategory': '化妝品'},
    {'floor': '1F', 'brand_name': 'LANCÔME', 'brand_name_ko': '랑콤', 'brand_name_en': 'LANCÔME', 'category': '化妝品', 'subcategory': '化妝品'},
    {'floor': '1F', 'brand_name': 'Kiehl\'s', 'brand_name_ko': '키엘', 'brand_name_en': "Kiehl's", 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'Guerlain', 'brand_name_ko': '게를랭', 'brand_name_en': 'Guerlain', 'category': '化妝品', 'subcategory': '香水'},
    {'floor': '1F', 'brand_name': 'Bourjois', 'brand_name_ko': '뽀아레', 'brand_name_en': 'Bourjois', 'category': '化妝品', 'subcategory': '彩妝'},
    {'floor': '1F', 'brand_name': 'Swiss Perfection', 'brand_name_ko': '스위스퍼펙션', 'brand_name_en': 'Swiss Perfection', 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'Le Labo', 'brand_name_ko': '르라보', 'brand_name_en': 'Le Labo', 'category': '化妝品', 'subcategory': '香水'},
    {'floor': '1F', 'brand_name': 'The Hour Glass', 'brand_name_ko': '더아워글래스', 'brand_name_en': 'THE HOUR GLASS', 'category': '化妝品', 'subcategory': '香水/護膚'},
    {'floor': '1F', 'brand_name': 'Clé de Peau', 'brand_name_ko': '클드포', 'brand_name_en': 'Clé de Peau', 'category': '化妝品', 'subcategory': '護膚'},
    {'floor': '1F', 'brand_name': 'Shu Uemura', 'brand_name_ko': '쉬우무라', 'brand_name_en': 'Shu Uemura', 'category': '化妝品', 'subcategory': '彩妝'},
    {'floor': '1F', 'brand_name': 'Decathlon', 'brand_name_ko': '데카슬론', 'brand_name_en': 'Decathlon', 'category': '運動', 'subcategory': '戶外運動'},
    # ======================== 2F ========================
    {'floor': '2F', 'brand_name': 'Cartier', 'brand_name_ko': '까르띠에', 'brand_name_en': 'Cartier', 'category': '珠寶', 'subcategory': '戒指/腕錶'},
    {'floor': '2F', 'brand_name': 'Van Cleef & Arpels', 'brand_name_ko': '반클리프앤아펠', 'brand_name_en': 'Van Cleef & Arpels', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Tiffany & Co.', 'brand_name_ko': '티파니', 'brand_name_en': 'Tiffany & Co.', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Bulgari', 'brand_name_ko': '불가리', 'brand_name_en': 'Bulgari', 'category': '珠寶', 'subcategory': '珠寶/腕錶'},
    {'floor': '2F', 'brand_name': 'Graff', 'brand_name_ko': '그라프', 'brand_name_en': 'Graff', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Chaumet', 'brand_name_ko': '쇼메', 'brand_name_en': 'Chaumet', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'FRED', 'brand_name_ko': '프레다이아', 'brand_name_en': 'FRED', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Damiani', 'brand_name_ko': '다미아니', 'brand_name_en': 'Damiani', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Buccellati', 'brand_name_ko': '부첼라티', 'brand_name_en': 'Buccellati', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Boucheron', 'brand_name_ko': '부쉐론', 'brand_name_en': 'Boucheron', 'category': '珠寶', 'subcategory': '珠寶'},
    {'floor': '2F', 'brand_name': 'Patek Philippe', 'brand_name_ko': '파텍필립', 'brand_name_en': 'Patek Philippe', 'category': '腕錶', 'subcategory': '頂級腕錶'},
    {'floor': '2F', 'brand_name': 'Vacheron Constantin', 'brand_name_ko': '바쉐론콘스탄틴', 'brand_name_en': 'Vacheron Constantin', 'category': '腕錶', 'subcategory': '頂級腕錶'},
    {'floor': '2F', 'brand_name': 'Breguet', 'brand_name_ko': '브레게', 'brand_name_en': 'Breguet', 'category': '腕錶', 'subcategory': '頂級腕錶'},
    {'floor': '2F', 'brand_name': 'Rolex', 'brand_name_ko': '롤렉스', 'brand_name_en': 'Rolex', 'category': '腕錶', 'subcategory': '名錶'},
    {'floor': '2F', 'brand_name': 'OMEGA', 'brand_name_ko': '오메가', 'brand_name_en': 'OMEGA', 'category': '腕錶', 'subcategory': '名錶'},
    {'floor': '2F', 'brand_name': 'IWC', 'brand_name_ko': '아이더블유씨', 'brand_name_en': 'IWC', 'category': '腕錶', 'subcategory': '名錶'},
    {'floor': '2F', 'brand_name': 'Piaget', 'brand_name_ko': '피아제', 'brand_name_en': 'Piaget', 'category': '腕錶', 'subcategory': '珠寶/腕錶'},
    {'floor': '2F', 'brand_name': 'Jaquet Droz', 'brand_name_ko': '자케드러즈', 'brand_name_en': 'Jaquet Droz', 'category': '腕錶', 'subcategory': '頂級腕錶'},
    {'floor': '2F', 'brand_name': 'TAG Heuer', 'brand_name_ko': '태그호이어', 'brand_name_en': 'TAG Heuer', 'category': '腕錶', 'subcategory': '運動錶'},
    {'floor': '2F', 'brand_name': 'Grand Seiko', 'brand_name_ko': '그랜드세이코', 'brand_name_en': 'Grand Seiko', 'category': '腕錶', 'subcategory': '日本名錶'},
    {'floor': '2F', 'brand_name': 'Longines', 'brand_name_ko': '롱인', 'brand_name_en': 'Longines', 'category': '腕錶', 'subcategory': '瑞士錶'},
    {'floor': '2F', 'brand_name': 'Tudor', 'brand_name_ko': '튜더', 'brand_name_en': 'Tudor', 'category': '腕錶', 'subcategory': '腕錶'},
    {'floor': '2F', 'brand_name': 'Moncler', 'brand_name_ko': '몽클레르', 'brand_name_en': 'Moncler', 'category': '時裝', 'subcategory': '羽絨'},
    {'floor': '2F', 'brand_name': 'Jimmy Choo', 'brand_name_ko': '지미추', 'brand_name_en': 'Jimmy Choo', 'category': '精品', 'subcategory': '鞋類/包包'},
    {'floor': '2F', 'brand_name': 'Celine', 'brand_name_ko': '셀린느', 'brand_name_en': 'Celine', 'category': '精品', 'subcategory': '時裝'},
    {'floor': '2F', 'brand_name': 'Loewe', 'brand_name_ko': '로에베', 'brand_name_en': 'Loewe', 'category': '精品', 'subcategory': '皮革'},
    {'floor': '2F', 'brand_name': 'Loro Piana', 'brand_name_ko': '로로피아나', 'brand_name_en': 'Loro Piana', 'category': '精品', 'subcategory': '羊絨'},
    {'floor': '2F', 'brand_name': 'KENZO', 'brand_name_ko': '겐조', 'brand_name_en': 'KENZO', 'category': '時裝', 'subcategory': '男女裝'},
    {'floor': '2F', 'brand_name': 'Marc Jacobs', 'brand_name_ko': '마크모스', 'brand_name_en': 'Marc Jacobs', 'category': '精品', 'subcategory': '包包/時裝'},
    {'floor': '2F', 'brand_name': 'Acne Studios', 'brand_name_ko': '아크네스튜디오', 'brand_name_en': 'Acne Studios', 'category': '時裝', 'subcategory': '設計師品牌'},
    {'floor': '2F', 'brand_name': 'Ami Paris', 'brand_name_ko': '아미파리', 'brand_name_en': 'Ami Paris', 'category': '時裝', 'subcategory': '法國男裝'},
    {'floor': '2F', 'brand_name': 'A.P.C.', 'brand_name_ko': '에이피세', 'brand_name_en': 'A.P.C.', 'category': '時裝', 'subcategory': '法國休閒'},
    {'floor': '2F', 'brand_name': 'Isabel Marant', 'brand_name_ko': '이자벨마랑', 'brand_name_en': 'Isabel Marant', 'category': '時裝', 'subcategory': '法國女裝'},
    {'floor': '2F', 'brand_name': 'BOSS', 'brand_name_ko': '보스', 'brand_name_en': 'BOSS', 'category': '時裝', 'subcategory': '男性正裝'},
    {'floor': '2F', 'brand_name': 'Nike', 'brand_name_ko': '나이키', 'brand_name_en': 'Nike', 'category': '運動', 'subcategory': '運動鞋'},
    {'floor': '2F', 'brand_name': 'Adidas', 'brand_name_ko': '아디다스', 'brand_name_en': 'Adidas', 'category': '運動', 'subcategory': '運動鞋'},
    {'floor': '2F', 'brand_name': 'New Balance', 'brand_name_ko': '뉴발란스', 'brand_name_en': 'New Balance', 'category': '運動', 'subcategory': '運動鞋'},
    {'floor': '2F', 'brand_name': 'J.ESTINA', 'brand_name_ko': '제이에스티나', 'brand_name_en': 'J.ESTINA', 'category': '珠寶', 'subcategory': '韓國飾品'},
    # ======================== 3F ========================
    {'floor': '3F', 'brand_name': 'Ader Error', 'brand_name_ko': '아더에러', 'brand_name_en': 'Ader Error', 'category': '設計師', 'subcategory': '韓國新銳'},
    {'floor': '3F', 'brand_name': 'Sandro', 'brand_name_ko': '산드로', 'brand_name_en': 'Sandro', 'category': '設計師', 'subcategory': '法國女裝'},
    {'floor': '3F', 'brand_name': 'Maje', 'brand_name_ko': '마주', 'brand_name_en': 'Maje', 'category': '設計師', 'subcategory': '法國女裝'},
    {'floor': '3F', 'brand_name': 'Claudie Pierlot', 'brand_name_ko': '클로디피에르', 'brand_name_en': 'Claudie Pierlot', 'category': '設計師', 'subcategory': '法國女裝'},
    {'floor': '3F', 'brand_name': 'IRO', 'brand_name_ko': '이로', 'brand_name_en': 'IRO', 'category': '設計師', 'subcategory': '法國男女裝'},
    {'floor': '3F', 'brand_name': 'The Row', 'brand_name_ko': '더로', 'brand_name_en': 'The Row', 'category': '設計師', 'subcategory': '美國極簡'},
    {'floor': '3F', 'brand_name': 'Totême', 'brand_name_ko': '토텀', 'brand_name_en': 'Totême', 'category': '設計師', 'subcategory': '北歐極簡'},
    {'floor': '3F', 'brand_name': 'Ganni', 'brand_name_ko': '가니', 'brand_name_en': 'Ganni', 'category': '設計師', 'subcategory': '丹麥女裝'},
    {'floor': '3F', 'brand_name': 'Ba&sh', 'brand_name_ko': '바쉬', 'brand_name_en': 'Ba&sh', 'category': '設計師', 'subcategory': '法國女裝'},
    {'floor': '3F', 'brand_name': 'Self-Portrait', 'brand_name_ko': '셀프포트레이트', 'brand_name_en': 'Self-Portrait', 'category': '設計師', 'subcategory': '英國女裝'},
    {'floor': '3F', 'brand_name': 'Miss Sixty', 'brand_name_ko': '미스식스티', 'brand_name_en': 'Miss Sixty', 'category': '時裝', 'subcategory': '女裝'},
    {'floor': '3F', 'brand_name': 'O\'2nd', 'brand_name_ko': '오세컨드', 'brand_name_en': "O'2nd", 'category': '時裝', 'subcategory': '韓國女裝'},
    {'floor': '3F', 'brand_name': 'SJSJ', 'brand_name_ko': '에스제이에스제이', 'brand_name_en': 'SJSJ', 'category': '時裝', 'subcategory': '韓國女裝'},
    {'floor': '3F', 'brand_name': 'Uniqlo', 'brand_name_ko': '유니클로', 'brand_name_en': 'Uniqlo', 'category': '休閒', 'subcategory': '平價服飾'},
    {'floor': '3F', 'brand_name': 'Gap', 'brand_name_ko': '갭', 'brand_name_en': 'Gap', 'category': '休閒', 'subcategory': '美式休閒'},
    {'floor': '3F', 'brand_name': 'Tommy Hilfiger', 'brand_name_ko': '토미힐피거', 'brand_name_en': 'Tommy Hilfiger', 'category': '休閒', 'subcategory': '美式學院風'},
    {'floor': '3F', 'brand_name': 'Calvin Klein', 'brand_name_ko': '캘빈클라인', 'brand_name_en': 'Calvin Klein', 'category': '休閒', 'subcategory': '內衣/休閒'},
    # ======================== 4F ========================
    {'floor': '4F', 'brand_name': 'The North Face', 'brand_name_ko': '노스페이스', 'brand_name_en': 'The North Face', 'category': '戶外', 'subcategory': '機能外套'},
    {'floor': '4F', 'brand_name': 'Columbia', 'brand_name_ko': '컬럼비아', 'brand_name_en': 'Columbia', 'category': '戶外', 'subcategory': '機能外套'},
    {'floor': '4F', 'brand_name': 'Salomon', 'brand_name_ko': '살로몬', 'brand_name_en': 'Salomon', 'category': '戶外', 'subcategory': '越野跑/滑雪'},
    {'floor': '4F', 'brand_name': 'Arc\'teryx', 'brand_name_ko': '아크테릭스', 'brand_name_en': "Arc'teryx", 'category': '戶外', 'subcategory': '頂級戶外'},
    {'floor': '4F', 'brand_name': 'Patagonia', 'brand_name_ko': '파타고니아', 'brand_name_en': 'Patagonia', 'category': '戶外', 'subcategory': '環保戶外'},
    {'floor': '4F', 'brand_name': 'Mammut', 'brand_name_ko': '마모트', 'brand_name_en': 'Mammut', 'category': '戶外', 'subcategory': '瑞士戶外'},
    {'floor': '4F', 'brand_name': 'La Sportiva', 'brand_name_ko': '라스포르티바', 'brand_name_en': 'La Sportiva', 'category': '戶外', 'subcategory': '登山/攀岩'},
    {'floor': '4F', 'brand_name': 'Black Diamond', 'brand_name_ko': '블랙다이아', 'brand_name_en': 'Black Diamond', 'category': '戶外', 'subcategory': '攀岩裝備'},
    {'floor': '4F', 'brand_name': 'Nike', 'brand_name_ko': '나이키', 'brand_name_en': 'Nike', 'category': '運動', 'subcategory': '運動鞋/服飾'},
    {'floor': '4F', 'brand_name': 'Adidas', 'brand_name_ko': '아디다스', 'brand_name_en': 'Adidas', 'category': '運動', 'subcategory': '運動鞋/服飾'},
    {'floor': '4F', 'brand_name': 'New Balance', 'brand_name_ko': '뉴발란스', 'brand_name_en': 'New Balance', 'category': '運動', 'subcategory': '運動鞋'},
    {'floor': '4F', 'brand_name': 'Converse', 'brand_name_ko': '컨버스', 'brand_name_en': 'Converse', 'category': '運動', 'subcategory': '帆布鞋'},
    {'floor': '4F', 'brand_name': 'Vans', 'brand_name_ko': '반스', 'brand_name_en': 'Vans', 'category': '運動', 'subcategory': '滑板鞋'},
    {'floor': '4F', 'brand_name': 'Fila', 'brand_name_ko': '휠라', 'brand_name_en': 'Fila', 'category': '運動', 'subcategory': '運動休閒'},
    {'floor': '4F', 'brand_name': 'Puma', 'brand_name_ko': '푸마', 'brand_name_en': 'Puma', 'category': '運動', 'subcategory': '運動休閒'},
    {'floor': '4F', 'brand_name': 'Asics', 'brand_name_ko': '아식스', 'brand_name_en': 'Asics', 'category': '運動', 'subcategory': '跑鞋'},
    {'floor': '4F', 'brand_name': 'Under Armour', 'brand_name_ko': '언더아모어', 'brand_name_en': 'Under Armour', 'category': '運動', 'subcategory': '機能運動'},
    {'floor': '4F', 'brand_name': 'Descente', 'brand_name_ko': '데상트', 'brand_name_en': 'Descente', 'category': '運動', 'subcategory': '高爾夫/滑雪'},
    {'floor': '4F', 'brand_name': 'Le Coq Sportif', 'brand_name_ko': '르코크스포르티프', 'brand_name_en': 'Le Coq Sportif', 'category': '運動', 'subcategory': '法國運動'},
    {'floor': '4F', 'brand_name': 'Kappa', 'brand_name_ko': '카파', 'brand_name_en': 'Kappa', 'category': '運動', 'subcategory': '義大利運動'},
    # ======================== 5F ========================
    {'floor': '5F', 'brand_name': 'Burberry', 'brand_name_ko': '버버리', 'brand_name_en': 'Burberry', 'category': '精品', 'subcategory': '男性西裝'},
    {'floor': '5F', 'brand_name': 'Brioni', 'brand_name_ko': '브리오니', 'brand_name_en': 'Brioni', 'category': '精品', 'subcategory': '義大利西裝'},
    {'floor': '5F', 'brand_name': 'Ermenegildo Zegna', 'brand_name_ko': '어메네질도제그나', 'brand_name_en': 'Ermenegildo Zegna', 'category': '精品', 'subcategory': '義大利西裝'},
    {'floor': '5F', 'brand_name': 'Tom Ford', 'brand_name_ko': '톰포트', 'brand_name_en': 'Tom Ford', 'category': '精品', 'subcategory': '男性西裝/香水'},
    {'floor': '5F', 'brand_name': 'Ralph Lauren', 'brand_name_ko': '랄프로렌', 'brand_name_en': 'Ralph Lauren', 'category': '時裝', 'subcategory': '美式學院'},
    {'floor': '5F', 'brand_name': 'BOSS', 'brand_name_ko': '보스', 'brand_name_en': 'BOSS', 'category': '時裝', 'subcategory': '男性正裝'},
    {'floor': '5F', 'brand_name': 'Canali', 'brand_name_ko': '카날리', 'brand_name_en': 'Canali', 'category': '精品', 'subcategory': '義大利西裝'},
    {'floor': '5F', 'brand_name': 'Finamore', 'brand_name_ko': '피나모레', 'brand_name_en': 'Finamore', 'category': '精品', 'subcategory': '義大利襯衫'},
    {'floor': '5F', 'brand_name': 'Drakes', 'brand_name_ko': '드레이크스', 'brand_name_en': 'Drakes', 'category': '時裝', 'subcategory': '英國領帶/西裝'},
    {'floor': '5F', 'brand_name': 'Jil Stuart', 'brand_name_ko': '질스튜어트', 'brand_name_en': 'Jil Stuart', 'category': '時裝', 'subcategory': '男性時裝'},
    {'floor': '5F', 'brand_name': 'Tricker\'s', 'brand_name_ko': '트리커스', 'brand_name_en': "Tricker's", 'category': '鞋', 'subcategory': '英國紳士鞋'},
    {'floor': '5F', 'brand_name': 'Berluti', 'brand_name_ko': '베를루띠', 'brand_name_en': 'Berluti', 'category': '鞋', 'subcategory': '法國紳士鞋'},
    {'floor': '5F', 'brand_name': 'John Lobb', 'brand_name_ko': '존롭', 'brand_name_en': 'John Lobb', 'category': '鞋', 'subcategory': '英國訂製鞋'},
    {'floor': '5F', 'brand_name': 'Crockett & Jones', 'brand_name_ko': '크로켓존스', 'brand_name_en': 'Crockett & Jones', 'category': '鞋', 'subcategory': '英國手工鞋'},
    {'floor': '5F', 'brand_name': 'J.ESTINA', 'brand_name_ko': '제이에스티나', 'brand_name_en': 'J.ESTINA', 'category': '配件', 'subcategory': '韓國飾品'},
    # ======================== 6F ========================
    {'floor': '6F', 'brand_name': 'Baby Dior', 'brand_name_ko': '베이비디올', 'brand_name_en': 'Baby Dior', 'category': '童裝', 'subcategory': '奢侈品童裝'},
    {'floor': '6F', 'brand_name': 'Burberry Kids', 'brand_name_ko': '버버리키즈', 'brand_name_en': 'Burberry Kids', 'category': '童裝', 'subcategory': '童裝'},
    {'floor': '6F', 'brand_name': 'Fendi Kids', 'brand_name_ko': '펜디키즈', 'brand_name_en': 'Fendi Kids', 'category': '童裝', 'subcategory': '童裝'},
    {'floor': '6F', 'brand_name': 'Moncler Enfant', 'brand_name_ko': '몽클레르앙팡', 'brand_name_en': 'Moncler Enfant', 'category': '童裝', 'subcategory': '童裝羽絨'},
    {'floor': '6F', 'brand_name': 'Armani Junior', 'brand_name_ko': '아르마니주니어', 'brand_name_en': 'Armani Junior', 'category': '童裝', 'subcategory': '童裝'},
    {'floor': '6F', 'brand_name': 'Ralph Lauren Children', 'brand_name_ko': '랄프로렌칠드런', 'brand_name_en': 'Ralph Lauren Children', 'category': '童裝', 'subcategory': '童裝'},
    {'floor': '6F', 'brand_name': 'Gap Kids', 'brand_name_ko': '갭키즈', 'brand_name_en': 'Gap Kids', 'category': '童裝', 'subcategory': '童裝'},
    {'floor': '6F', 'brand_name': 'Nike Kids', 'brand_name_ko': '나이키키즈', 'brand_name_en': 'Nike Kids', 'category': '童裝', 'subcategory': '童裝運動'},
    {'floor': '6F', 'brand_name': 'Adidas Kids', 'brand_name_ko': '아디다스키즈', 'brand_name_en': 'Adidas Kids', 'category': '童裝', 'subcategory': '童裝運動'},
    {'floor': '6F', 'brand_name': 'Converse Kids', 'brand_name_ko': '컨버스키즈', 'brand_name_en': 'Converse Kids', 'category': '童裝', 'subcategory': '童裝鞋'},
    {'floor': '6F', 'brand_name': 'KidZania', 'brand_name_ko': '키자니아', 'brand_name_en': 'KidZania', 'category': '體驗', 'subcategory': '兒童職業體驗'},
    {'floor': '6F', 'brand_name': 'Callaway', 'brand_name_ko': '칼러웨이', 'brand_name_en': 'Callaway', 'category': '高爾夫', 'subcategory': '高爾夫球具'},
    {'floor': '6F', 'brand_name': 'Titleist', 'brand_name_ko': '타이틀리스트', 'brand_name_en': 'Titleist', 'category': '高爾夫', 'subcategory': '高爾夫球具'},
    {'floor': '6F', 'brand_name': 'TaylorMade', 'brand_name_ko': '테일러메이드', 'brand_name_en': 'TaylorMade', 'category': '高爾夫', 'subcategory': '高爾夫球具'},
    {'floor': '6F', 'brand_name': 'PING', 'brand_name_ko': '핑', 'brand_name_en': 'PING', 'category': '高爾夫', 'subcategory': '高爾夫球具'},
    {'floor': '6F', 'brand_name': 'Foot Joy', 'brand_name_ko': '풋조이', 'brand_name_en': 'Foot Joy', 'category': '高爾夫', 'subcategory': '高爾夫球鞋'},
    {'floor': '6F', 'brand_name': 'Lacoste', 'brand_name_ko': '라코스테', 'brand_name_en': 'Lacoste', 'category': '運動', 'subcategory': '法國鱷魚'},
    # ======================== 7F ========================
    {'floor': '7F', 'brand_name': 'Samsung', 'brand_name_ko': '삼성', 'brand_name_en': 'Samsung', 'category': '電子', 'subcategory': '電視/家電'},
    {'floor': '7F', 'brand_name': 'LG', 'brand_name_ko': 'LG', 'brand_name_en': 'LG', 'category': '電子', 'subcategory': '電視/家電'},
    {'floor': '7F', 'brand_name': 'Apple', 'brand_name_ko': '애플', 'brand_name_en': 'Apple', 'category': '電子', 'subcategory': '手機/電腦'},
    {'floor': '7F', 'brand_name': 'Dyson', 'brand_name_ko': '다이슨', 'brand_name_en': 'Dyson', 'category': '生活', 'subcategory': '家電/吹風機'},
    {'floor': '7F', 'brand_name': 'CGV', 'brand_name_ko': '시지비', 'brand_name_en': 'CGV', 'category': '影城', 'subcategory': '電影院'},
    {'floor': '7F', 'brand_name': 'LEGO', 'brand_name_ko': '레고', 'brand_name_en': 'LEGO', 'category': '玩具', 'subcategory': '樂高玩具'},
    {'floor': '7F', 'brand_name': 'Pottery Barn Kids', 'brand_name_ko': '포터리바arn', 'brand_name_en': 'Pottery Barn Kids', 'category': '家具', 'subcategory': '兒童家具'},
    # ======================== 8F ========================
    {'floor': '8F', 'brand_name': 'IKEA', 'brand_name_ko': '이케아', 'brand_name_en': 'IKEA', 'category': '家具', 'subcategory': '平價家具'},
    {'floor': '8F', 'brand_name': 'Samsung', 'brand_name_ko': '삼성', 'brand_name_en': 'Samsung', 'category': '電子', 'subcategory': '生活家電'},
    {'floor': '8F', 'brand_name': 'LG', 'brand_name_ko': 'LG', 'brand_name_en': 'LG', 'category': '電子', 'subcategory': '生活家電'},
    {'floor': '8F', 'brand_name': 'CGV IMAX', 'brand_name_ko': '시지비imax', 'brand_name_en': 'CGV IMAX', 'category': '影城', 'subcategory': 'IMAX電影院'},
    # ======================== 9F ========================
    {'floor': '9F', 'brand_name': '客戶服務中心', 'brand_name_ko': '고객서비스센터', 'brand_name_en': 'Customer Service', 'category': '服務', 'subcategory': '客戶服務'},
    # ======================== 10F ========================
    {'floor': '10F', 'brand_name': 'Trinity Spa', 'brand_name_ko': '트리니티스파', 'brand_name_en': 'Trinity Spa', 'category': '服務', 'subcategory': 'Spa/健身'},
    # ======================== 11F ========================
    {'floor': '11F', 'brand_name': 'Golf Range', 'brand_name_ko': '골프레인지', 'brand_name_en': 'Golf Range', 'category': '高爾夫', 'subcategory': '室內高爾夫練習場'},
]

# Rebuild DB
conn = sqlite3.connect(DB)
cur = conn.cursor()

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

now = time.strftime('%Y-%m-%d %H:%M')

# Insert brands with correct keys
for b in BRANDS:
    cur.execute('''INSERT INTO brands 
        (floor, brand_name, brand_name_ko, brand_name_en, category, subcategory, location_detail, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (b['floor'], b['brand_name'], b['brand_name_ko'], b['brand_name_en'],
         b['category'], b['subcategory'], b.get('location_detail', ''), now))

conn.commit()

# Stats
print('Brands by floor:')
cur.execute('SELECT floor, COUNT(*) FROM brands GROUP BY floor ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]} brands')

print(f'\nTotal: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]} brands')

# Search tests
print('\n=== Search Tests ===')
tests = ['Louis', 'Nike', '香奈兒', 'Cartier', '嬌蘭', '嬰童', '高爾夫']
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