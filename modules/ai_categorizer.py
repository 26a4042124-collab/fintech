import json
import os
import re
from datetime import datetime

CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'categories.json')

DEFAULT_RULES = {
    "cat_income_salary": {
        "keywords": ["LUONG", "THUONG", "CHUYEN LUONG", "SALARY", "BONUS", "THU NHAP"],
        "name": "Thu nhập tiền lương",
        "bucket": "INCOME"
    },
    "cat_needs_housing": {
        "keywords": ["THUE NHA", "TIEN DIEN", "EVN", "NUOC SACH", "INTERNET", "VNPT", "VIETTEL", "FPT", "DIEN THOAI TRA SAU"],
        "name": "Nhà ở & Hóa đơn tiện ích",
        "bucket": "NEEDS"
    },
    "cat_needs_food": {
        "keywords": ["WINMART", "COOPMART", "BACH HOA XANH", "THUC PHAM", "SIEU THI", "CHO "],
        "name": "Thực phẩm & Đi chợ",
        "bucket": "NEEDS"
    },
    "cat_wants_dining": {
        "keywords": ["HIGHLANDS", "PHUC LONG", "THE COFFEE HOUSE", "COM TRUA", "BUN CHA", "COM TAM", "PHO BO", "BUN DAU", "LAU MANWAH", "GRABFOOD", "SHOPEEFOOD"],
        "name": "Ăn uống & Cà phê ngoài",
        "bucket": "WANTS"
    },
    "cat_needs_transport": {
        "keywords": ["GRAB", "BE CAR", "BE BIKE", "XANH SM", "PETROLIMEX", "XANG", "GUI XE"],
        "name": "Đi lại & Xăng xe",
        "bucket": "NEEDS"
    },
    "cat_wants_shopping": {
        "keywords": ["SHOPEE", "TIKTOK SHOP", "LAZADA", "THOI TRANG", "MY PHAM", "TAI NGHE", "GIAY"],
        "name": "Mua sắm cá nhân",
        "bucket": "WANTS"
    },
    "cat_wants_subscription": {
        "keywords": ["NETFLIX", "SPOTIFY", "APPLE.COM/BILL", "ICLOUD", "YOUTUBE", "CHATGPT", "GYM"],
        "name": "Dịch vụ số định kỳ (Subscription)",
        "bucket": "WANTS"
    },
    "cat_wants_entertainment": {
        "keywords": ["CGV", "LOTTE CINEMA", "KARAOKE", "VE XEM PHIM", "DU LICH"],
        "name": "Giải trí & Phim ảnh",
        "bucket": "WANTS"
    },
    "cat_needs_healthcare": {
        "keywords": ["PHARMACITY", "LONG CHAU", "BENH VIEN", "KHAM BENH", "THUOC", "KHOA HOC", "TIENG ANH", "HOC PHI"],
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

def categorize_transaction(description, timestamp_str=""):
    """
    Mô hình AI/NLP xử lý ngôn ngữ tự nhiên:
    Đọc từ điển động từ categories.json -> gán nhãn danh mục và rổ 50/30/20.
    """
    desc_upper = description.upper()
    categories = load_categories()
    
    # 1. Quét danh mục động từ file cấu hình
    if categories:
        for cat in categories:
            # Bỏ qua nếu danh mục bị ẩn
            if cat.get("is_hidden", False):
                continue
                
            keywords = cat.get("keywords", [])
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', desc_upper) or kw in desc_upper:
                    night_flag = is_night_time(timestamp_str) and cat.get("bucket") == "WANTS"
                    is_sub = "SUBSCRIPTION" in cat.get("id", "").upper() or "ĐỊNH KỲ" in cat.get("name", "").upper()
                    return {
                        "rule_key": cat.get("id"),
                        "category": cat.get("name"),
                        "bucket": cat.get("bucket"),
                        "is_night_spending": night_flag,
                        "is_subscription": is_sub,
                        "confidence_score": 0.95
                    }
                    
    # 2. Fallback sang luật mặc định nếu file categories lỗi hoặc chưa khớp
    for rule_key, rule_data in DEFAULT_RULES.items():
        for kw in rule_data["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_upper) or kw in desc_upper:
                night_flag = is_night_time(timestamp_str) and rule_data["bucket"] == "WANTS"
                is_sub = "cat_wants_subscription" == rule_key
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
        else:
            cat_result = categorize_transaction(t_copy.get("description", ""), t_copy.get("timestamp", ""))
            t_copy["ai_category"] = cat_result["category"]
            t_copy["ai_bucket"] = cat_result["bucket"]
            t_copy["is_night_spending"] = cat_result["is_night_spending"]
            t_copy["is_subscription"] = cat_result["is_subscription"]
            t_copy["ai_confidence"] = cat_result["confidence_score"]
            
        enriched.append(t_copy)
    return enriched
