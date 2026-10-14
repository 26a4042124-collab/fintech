import re
from datetime import datetime

# Từ điển ánh xạ từ khóa (NLP Token Dictionary) trong chuyển khoản ngân hàng Việt Nam
CATEGORY_RULES = {
    "INCOME": {
        "keywords": ["LUONG", "THUONG", "CHUYEN LUONG", "SALARY", "BONUS", "THU NHAP"],
        "category_name": "Thu nhập tiền lương",
        "bucket": "INCOME"
    },
    "HOUSING_UTILITIES": {
        "keywords": ["THUE NHA", "TIEN DIEN", "EVN", "NUOC SACH", "INTERNET", "VNPT", "VIETTEL", "FPT", "DIEN THOAI TRA SAU"],
        "category_name": "Nhà ở & Hóa đơn tiện ích",
        "bucket": "NEEDS"
    },
    "FOOD_ESSENTIAL": {
        "keywords": ["WINMART", "COOPMART", "BACH HOA XANH", "THUC PHAM", "SIEU THI", "CHO "],
        "category_name": "Thực phẩm & Đi chợ",
        "bucket": "NEEDS"
    },
    "FOOD_DINING": {
        "keywords": ["HIGHLANDS", "PHUC LONG", "THE COFFEE HOUSE", "COM TRUA", "BUN CHA", "COM TAM", "PHO BO", "BUN DAU", "LAU MANWAH", "GRABFOOD", "SHOPEEFOOD"],
        "category_name": "Ăn uống & Cà phê ngoài",
        "bucket": "WANTS"
    },
    "TRANSPORT": {
        "keywords": ["GRAB", "BE CAR", "BE BIKE", "XANH SM", "PETROLIMEX", "XANG", "GUI XE"],
        "category_name": "Đi lại & Xăng xe",
        "bucket": "NEEDS"
    },
    "SHOPPING": {
        "keywords": ["SHOPEE", "TIKTOK SHOP", "LAZADA", "THOI TRANG", "MY PHAM", "TAI NGHE", "GIAY"],
        "category_name": "Mua sắm cá nhân",
        "bucket": "WANTS"
    },
    "DIGITAL_SUBSCRIPTION": {
        "keywords": ["NETFLIX", "SPOTIFY", "APPLE.COM/BILL", "ICLOUD", "YOUTUBE", "CHATGPT", "GYM"],
        "category_name": "Dịch vụ số định kỳ (Subscription)",
        "bucket": "WANTS"
    },
    "ENTERTAINMENT": {
        "keywords": ["CGV", "LOTTE CINEMA", "KARAOKE", "VE XEM PHIM", "DU LICH"],
        "category_name": "Giải trí & Phim ảnh",
        "bucket": "WANTS"
    },
    "HEALTHCARE_EDUCATION": {
        "keywords": ["PHARMACITY", "LONG CHAU", "BENH VIEN", "KHAM BENH", "THUOC", "KHOA HOC", "TIENG ANH", "HOC PHI"],
        "category_name": "Y tế & Giáo dục",
        "bucket": "NEEDS"
    },
    "SAVINGS_INVESTMENT": {
        "keywords": ["TIET KIEM", "TICH LUY", "CHUNG CHI QUY", "DAU TU", "SAVINGS"],
        "category_name": "Tiết kiệm & Tích sản",
        "bucket": "SAVINGS"
    }
}

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
    Phân tích chuỗi văn bản không dấu của ngân hàng -> gán nhãn danh mục và rổ 50/30/20.
    """
    desc_upper = description.upper()
    
    # Quét qua các tập luật từ điển
    for rule_key, rule_data in CATEGORY_RULES.items():
        for kw in rule_data["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_upper) or kw in desc_upper:
                night_flag = is_night_time(timestamp_str) and rule_data["bucket"] == "WANTS"
                is_sub = rule_key == "DIGITAL_SUBSCRIPTION"
                return {
                    "rule_key": rule_key,
                    "category": rule_data["category_name"],
                    "bucket": rule_data["bucket"],
                    "is_night_spending": night_flag,
                    "is_subscription": is_sub,
                    "confidence_score": 0.94
                }
                
    # Mặc định nếu không khớp từ khóa
    return {
        "rule_key": "OTHER_EXPENSES",
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
