import json
import os
import re
import unicodedata
from datetime import datetime

CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'categories.json')

def remove_accents(input_str):
    """Loại bỏ dấu tiếng Việt để đối sánh từ khóa linh hoạt."""
    if not input_str:
        return ""
    nfkd = unicodedata.normalize('NFKD', input_str)
    res = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return res.replace('đ', 'd').replace('Đ', 'D')

DEFAULT_RULES = {
    "cat_income_salary": {
        "keywords": ["CHUYEN LUONG", "TIEN LUONG", "BANG LUONG", "SALARY", "BONUS", "THUONG", "THU NHAP", "PAYROLL"],
        "name": "Thu nhập tiền lương",
        "bucket": "INCOME"
    },
    "cat_needs_housing": {
        "keywords": ["THUE NHA", "TIEN DIEN", "EVN", "NUOC SACH", "INTERNET", "VNPT", "VIETTEL", "FPT", "DIEN THOAI TRA SAU", "HOA DON SINH HOAT", "HOA DON", "TIEN NHA"],
        "name": "Nhà ở & Hóa đơn tiện ích",
        "bucket": "NEEDS"
    },
    "cat_needs_food": {
        "keywords": ["WINMART", "COOPMART", "BACH HOA XANH", "THUC PHAM", "SIEU THI", "CHO ", "DI CHO"],
        "name": "Thực phẩm & Đi chợ",
        "bucket": "NEEDS"
    },
    "cat_wants_dining": {
        "keywords": ["HIGHLANDS", "PHUC LONG", "THE COFFEE HOUSE", "COM TRUA", "BUN CHA", "COM TAM", "PHO BO", "BUN DAU", "LAU MANWAH", "GRABFOOD", "SHOPEEFOOD", "AN UONG", "CA PHE", "TRA SUA", "QUAN AN", "NHA HANG"],
        "name": "Ăn uống & Cà phê ngoài",
        "bucket": "WANTS"
    },
    "cat_needs_transport": {
        "keywords": ["GRAB", "BE CAR", "BE BIKE", "XANH SM", "PETROLIMEX", "XANG", "GUI XE", "DI LAI", "XANG XE"],
        "name": "Đi lại & Xăng xe",
        "bucket": "NEEDS"
    },
    "cat_wants_shopping": {
        "keywords": ["SHOPEE", "TIKTOK SHOP", "LAZADA", "THOI TRANG", "MY PHAM", "TAI NGHE", "GIAY", "MUA SAM", "QUAN AO"],
        "name": "Mua sắm cá nhân",
        "bucket": "WANTS"
    },
    "cat_wants_subscription": {
        "keywords": ["NETFLIX", "SPOTIFY", "APPLE.COM/BILL", "ICLOUD", "YOUTUBE", "CHATGPT", "GYM", "SUBSCRIPTION", "DINH KY"],
        "name": "Dịch vụ số định kỳ (Subscription)",
        "bucket": "WANTS"
    },
    "cat_wants_entertainment": {
        "keywords": ["CGV", "LOTTE CINEMA", "KARAOKE", "VE XEM PHIM", "DU LICH", "GIAI TRI", "XEM PHIM"],
        "name": "Giải trí & Phim ảnh",
        "bucket": "WANTS"
    },
    "cat_needs_healthcare": {
        "keywords": ["PHARMACITY", "LONG CHAU", "BENH VIEN", "KHAM BENH", "THUOC", "KHOA HOC", "TIENG ANH", "HOC PHI", "SUC KHOE", "NHA THUOC"],
        "name": "Y tế & Giáo dục",
        "bucket": "NEEDS"
    },
    "cat_savings_investment": {
        "keywords": ["TIET KIEM", "TICH LUY", "CHUNG CHI QUY", "DAU TU", "SAVINGS"],
        "name": "Tiết kiệm & Tích sản",
        "bucket": "SAVINGS"
    }
}

def load_categories():
    if not os.path.exists(CATEGORIES_FILE):
        return []
    try:
        with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_categories(categories):
    try:
        with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving categories: {e}")
        return False

def is_night_time(timestamp_str):
    """
    Kiểm tra xem giao dịch có diễn ra vào khung giờ đêm (22h00 - 04h00 sáng)
    để phát hiện chi tiêu bốc đồng (Impulse Spending).
    """
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        return hour >= 22 or hour < 4
    except Exception:
        return False

def categorize_transaction(description, timestamp_str="", txn_type="OUTFLOW"):
    """
    Mô hình AI/NLP xử lý ngôn ngữ tự nhiên:
    Đọc từ điển động từ categories.json -> gán nhãn danh mục và rổ 50/30/20.
    Loại bỏ dấu tiếng Việt và nhận diện chính xác các trường hợp ngoại lệ.
    """
    desc_upper = description.upper()
    desc_ascii = remove_accents(desc_upper)
    categories = load_categories()

    # Nhận diện subscription sớm để tránh false-positives
    is_sub_desc = any(sk in desc_ascii for sk in ["NETFLIX", "SPOTIFY", "APPLE.COM/BILL", "ICLOUD", "YOUTUBE PREMIUM", "CHATGPT"])

    # 1. Quét danh mục động từ file cấu hình (ưu tiên Subscription lên trước nếu khớp)
    if categories:
        # Nếu là OUTFLOW, bỏ qua các danh mục có bucket hoặc type là INCOME
        cand_categories = categories
        if txn_type == "OUTFLOW":
            cand_categories = [c for c in categories if c.get("bucket") != "INCOME" and c.get("type") != "INCOME"]
            # Nếu có dấu hiệu subscription, ưu tiên xếp nhóm subscription lên trước
            if is_sub_desc:
                cand_categories = sorted(cand_categories, key=lambda c: 0 if ("SUBSCRIPTION" in c.get("id", "").upper() or "ĐỊNH KỲ" in c.get("name", "").upper()) else 1)

        for cat in cand_categories:
            if cat.get("is_hidden", False):
                continue
                
            keywords = cat.get("keywords", [])
            for kw in keywords:
                kw_upper = kw.upper()
                kw_ascii = remove_accents(kw_upper)

                # Bảo vệ keyword 'LUONG': không khớp 'DUNG LUONG' hoặc 'CHAT LUONG' hoặc 'SO LUONG'
                if kw_ascii == "LUONG":
                    if any(bad in desc_ascii for bad in ["DUNG LUONG", "CHAT LUONG", "SO LUONG", "KHOI LUONG"]):
                        continue

                matched = (
                    re.search(r'\b' + re.escape(kw_upper) + r'\b', desc_upper) or
                    kw_upper in desc_upper or
                    re.search(r'\b' + re.escape(kw_ascii) + r'\b', desc_ascii) or
                    kw_ascii in desc_ascii
                )

                if matched:
                    is_sub = "SUBSCRIPTION" in cat.get("id", "").upper() or "ĐỊNH KỲ" in cat.get("name", "").upper() or is_sub_desc
                    # Subscriptions gia hạn ban đêm không phải chi tiêu bốc đồng
                    night_flag = False if is_sub else (is_night_time(timestamp_str) and cat.get("bucket") == "WANTS")
                    return {
                        "rule_key": cat.get("id"),
                        "category": cat.get("name"),
                        "bucket": cat.get("bucket"),
                        "is_night_spending": night_flag,
                        "is_subscription": is_sub,
                        "confidence_score": 0.95
                    }
                    
    # 2. Fallback sang luật mặc định nếu file categories lỗi hoặc chưa khớp
    cand_rules = DEFAULT_RULES
    if txn_type == "OUTFLOW":
        cand_rules = {k: v for k, v in DEFAULT_RULES.items() if v.get("bucket") != "INCOME"}
        if is_sub_desc:
            cand_rules = dict(sorted(cand_rules.items(), key=lambda kv: 0 if kv[0] == "cat_wants_subscription" else 1))

    for rule_key, rule_data in cand_rules.items():
        for kw in rule_data["keywords"]:
            kw_upper = kw.upper()
            kw_ascii = remove_accents(kw_upper)

            if kw_ascii == "LUONG":
                if any(bad in desc_ascii for bad in ["DUNG LUONG", "CHAT LUONG", "SO LUONG", "KHOI LUONG"]):
                    continue

            matched = (
                re.search(r'\b' + re.escape(kw_upper) + r'\b', desc_upper) or
                kw_upper in desc_upper or
                re.search(r'\b' + re.escape(kw_ascii) + r'\b', desc_ascii) or
                kw_ascii in desc_ascii
            )

            if matched:
                is_sub = "cat_wants_subscription" == rule_key or is_sub_desc
                night_flag = False if is_sub else (is_night_time(timestamp_str) and rule_data["bucket"] == "WANTS")
                return {
                    "rule_key": rule_key,
                    "category": rule_data["name"],
                    "bucket": rule_data["bucket"],
                    "is_night_spending": night_flag,
                    "is_subscription": is_sub,
                    "confidence_score": 0.92
                }

    # 3. Mặc định nếu không khớp từ khóa
    return {
        "rule_key": "cat_wants_other",
        "category": "Chi tiêu khác",
        "bucket": "WANTS",
        "is_night_spending": is_night_time(timestamp_str),
        "is_subscription": False,
        "confidence_score": 0.70
    }

def process_all_transactions(transactions):
    """
    Xử lý gán nhãn toàn bộ danh sách giao dịch đầu vào.
    """
    enriched = []
    for t in transactions:
        t_copy = dict(t)
        if t_copy.get("type") == "INFLOW":
            t_copy["ai_category"] = "Thu nhập tiền lương"
            t_copy["ai_bucket"] = "INCOME"
            t_copy["is_night_spending"] = False
            t_copy["is_subscription"] = False
            t_copy["ai_confidence"] = 0.98
        else:
            cat_result = categorize_transaction(
                t_copy.get("description", ""), 
                t_copy.get("timestamp", ""),
                txn_type=t_copy.get("type", "OUTFLOW")
            )
            t_copy["ai_category"] = cat_result["category"]
            t_copy["ai_bucket"] = cat_result["bucket"]
            t_copy["is_night_spending"] = cat_result["is_night_spending"]
            t_copy["is_subscription"] = cat_result["is_subscription"]
            t_copy["ai_confidence"] = cat_result["confidence_score"]
            
        enriched.append(t_copy)
    return enriched
