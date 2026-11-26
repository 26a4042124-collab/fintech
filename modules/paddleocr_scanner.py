"""
Module quét hóa đơn bằng EasyOCR (không cần API key, chạy local).

Chức năng chính:
- Dùng EasyOCR để OCR hóa đơn
- Phân tích và trích xuất dữ liệu có cấu trúc
- Hỗ trợ tiếng Việt
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO

try:
    from PIL import Image, ImageOps, ImageEnhance
except ImportError:
    raise ImportError("Cần cài đặt Pillow: pip install pillow")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Cấu hình logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Danh sách rổ chi tiêu mặc định
DEFAULT_CATEGORIES = [
    'Ăn uống', 'Cà phê', 'Đi lại', 'Mua sắm', 
    'Hóa đơn sinh hoạt', 'Giải trí', 'Sức khỏe', 
    'Giáo dục', 'Khác'
]

# Initialize EasyOCR globally (chạy lần đầu sẽ download model)
_ocr_reader = None

def get_ocr_reader():
    """Lấy OCR reader (lazy loading)"""
    global _ocr_reader
    if _ocr_reader is None and EASYOCR_AVAILABLE:
        try:
            logger.info("Khởi tạo EasyOCR reader...")
            _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)
            logger.info("✓ EasyOCR reader sẵn sàng")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo EasyOCR: {e}")
            _ocr_reader = None
    return _ocr_reader


class ReceiptProcessingError(Exception):
    """Lỗi xử lý ảnh hóa đơn"""
    pass


def preprocess_image(file_or_bytes) -> bytes:
    """
    Chuẩn hóa ảnh trước khi OCR.
    
    Args:
        file_or_bytes: File object hoặc bytes của ảnh
        
    Returns:
        bytes: Ảnh JPEG đã chuẩn hóa
        
    Raises:
        ReceiptProcessingError: Khi ảnh không hợp lệ
    """
    try:
        # Mở ảnh
        if isinstance(file_or_bytes, bytes):
            img = Image.open(BytesIO(file_or_bytes))
        else:
            img = Image.open(file_or_bytes)
        
        # Xoay đúng chiều theo EXIF
        img = ImageOps.exif_transpose(img)
        
        # Chuyển sang RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize nếu quá lớn
        width, height = img.size
        max_dim = 2000  # PaddleOCR xử lý được ảnh lớn hơn Gemini
        if max(width, height) > max_dim:
            ratio = max_dim / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Đã resize ảnh từ {width}x{height} xuống {new_size[0]}x{new_size[1]}")
        
        # Tăng nhẹ độ tương phản
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        
        # Nén JPEG
        output = BytesIO()
        img.save(output, format='JPEG', quality=90, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Lỗi xử lý ảnh: {str(e)}")
        raise ReceiptProcessingError(f"Không thể xử lý ảnh: {str(e)}")


def scan_receipt_paddle(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Quét hóa đơn bằng EasyOCR.
    
    Args:
        image_bytes: Ảnh đã chuẩn hóa (JPEG bytes)
        categories: Danh sách rổ chi tiêu được phép
        
    Returns:
        dict: Dữ liệu hóa đơn có cấu trúc
    """
    if not EASYOCR_AVAILABLE:
        raise ImportError("Thiếu thư viện easyocr")
    
    categories = categories or DEFAULT_CATEGORIES
    reader = get_ocr_reader()
    
    if reader is None:
        raise RuntimeError("Không thể khởi tạo EasyOCR")
    
    try:
        # Chuyển bytes thành ảnh để OCR
        from io import BytesIO
        import numpy as np
        
        img = Image.open(BytesIO(image_bytes))
        img_array = np.array(img)
        
        # OCR
        logger.info("Bắt đầu OCR bằng EasyOCR...")
        result = reader.readtext(img_array, detail=1)
        
        # Parse kết quả
        extracted_text = ""
        for detection in result:
            text = detection[1]
            confidence = detection[2]
            if confidence > 0.3:  # Chỉ lấy text có confidence > 30%
                extracted_text += text + " "
        
        logger.info(f"OCR text: {extracted_text[:200]}...")
        
        # Parse dữ liệu từ text
        parsed = _parse_receipt_text(extracted_text, categories)
        parsed['source'] = 'easyocr'
        
        return parsed
        
    except Exception as e:
        logger.error(f"Lỗi EasyOCR: {str(e)}")
        raise


def _parse_receipt_text(text: str, categories: List[str]) -> Dict[str, Any]:
    """
    Parse dữ liệu hóa đơn từ text OCR.
    """
    text_upper = text.upper()
    
    # Tìm số tiền (tìm số lớn nhất cuối cùng - thường là tổng)
    amounts = re.findall(r'(\d{2,})[.,]?(\d{0,3})(?:\s*(?:đ|VND|D))?', text)
    total_amount = 0
    if amounts:
        # Lấy số cuối cùng (thường là tổng)
        last_amount = amounts[-1]
        amount_str = last_amount[0]
        if last_amount[1]:
            amount_str += last_amount[1]
        total_amount = int(amount_str) if len(last_amount[0]) >= 3 else 0
    
    # Tìm tên cửa hàng (dòng đầu tiên hoặc chữ in hoa liên tiếp)
    merchant = "Hóa đơn"
    lines = text.split('\n')
    if lines:
        merchant = lines[0].strip()[:50]
    
    # Tìm ngày giờ
    timestamp = None
    date_patterns = [
        r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})',  # DD/MM/YYYY
        r'(\d{2,4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                parts = match.groups()
                if len(parts[2]) == 2:
                    year = int(parts[2]) + 2000
                else:
                    year = int(parts[2])
                month = int(parts[1])
                day = int(parts[0])
                dt = datetime(year, month, day, 12, 0, 0)
                timestamp = dt.isoformat()
                break
            except:
                pass
    
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    # Phân loại danh mục
    category = _categorize_receipt(text_upper, categories)
    
    # Tìm danh sách món (đơn giản: các dòng có giá)
    items = []
    for line in lines:
        if re.search(r'\d+', line):  # Dòng có chứa số
            # Tìm giá tiền trong dòng
            price_match = re.search(r'(\d+)\s*(?:đ|VND)?(?:\s|$)', line)
            if price_match:
                price = int(price_match.group(1))
                if price > 0 and price < total_amount:  # Tránh lấy tổng
                    item_name = re.sub(r'\d+.*', '', line).strip()
                    if len(item_name) > 2:
                        items.append({
                            'name': item_name[:50],
                            'quantity': 1,
                            'unit_price': price,
                            'amount': price,
                            'category': category
                        })
    
    # Nếu không tìm được items, tạo 1 item từ tổng
    if not items and total_amount > 0:
        items.append({
            'name': 'Tổng hóa đơn',
            'quantity': 1,
            'unit_price': total_amount,
            'amount': total_amount,
            'category': category
        })
    
    return {
        'merchant': merchant,
        'total_amount': total_amount,
        'timestamp': timestamp,
        'category': category,
        'items': items,
        'confidence': 0.75,  # PaddleOCR confidence
        'warnings': [
            'Dữ liệu OCR cục bộ - vui lòng kiểm tra kỹ trước khi lưu'
        ]
    }


def _categorize_receipt(text_upper: str, categories: List[str]) -> str:
    """
    Phân loại hóa đơn vào danh mục dựa trên từ khóa.
    """
    # Các từ khóa cho mỗi danh mục
    keywords = {
        'Cà phê': ['CAFE', 'COFFEE', 'HIGHLANDS', 'PHUC LONG', 'STARBUCKS', 'TRA', 'CAPPUCCINO'],
        'Ăn uống': ['PHO', 'COM', 'BUN', 'THUC PHAM', 'HANG', 'PIZZA', 'BANH', 'NUOC'],
        'Đi lại': ['XANG', 'PETROL', 'GRAB', 'TAXI', 'XE', 'VE', 'BOT'],
        'Mua sắm': ['SHOP', 'LAZADA', 'TIKTOK', 'QUAN AO', 'GIAY', 'MY PHAM'],
        'Hóa đơn sinh hoạt': ['DIEN', 'EVN', 'NUOC', 'INTERNET', 'HOA DON', 'TIEN'],
        'Giải trí': ['CGV', 'PHIM', 'GAME', 'NETFLIX', 'SPOTIFY', 'KARAOKE'],
        'Sức khỏe': ['BENH', 'THUOC', 'PHARMACY', 'KHAM', 'Y TE'],
        'Giáo dục': ['TRUONG', 'DAI HOC', 'KHOA HOC', 'GIAO DUC'],
    }
    
    for category, words in keywords.items():
        if category in categories:
            for word in words:
                if word in text_upper:
                    return category
    
    return 'Khác'


def scan_with_fallback_paddle(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Hàm điều phối: Thử PaddleOCR, không bao giờ fail.
    """
    categories = categories or DEFAULT_CATEGORIES
    
    try:
        result = scan_receipt_paddle(image_bytes, categories)
        logger.info(f"PaddleOCR scan thành công: {result.get('merchant')}, {len(result.get('items', []))} món")
        return result
        
    except Exception as e:
        logger.error(f"PaddleOCR thất bại, dùng fallback: {e}")
        return _get_fallback_sample(categories)


def _get_fallback_sample(categories: List[str]) -> Dict[str, Any]:
    """
    Trả dữ liệu mẫu khi PaddleOCR thất bại.
    """
    import random
    
    samples = [
        {
            'merchant': 'HIGHLANDS COFFEE',
            'items': [
                {'name': 'Cà phê đá', 'qty': 2, 'price': 35000},
                {'name': 'Bánh mì', 'qty': 1, 'price': 25000},
                {'name': 'Nước suối', 'qty': 2, 'price': 15000},
            ],
            'category': 'Cà phê'
        },
        {
            'merchant': 'PHỞ BÒ BẰNG',
            'items': [
                {'name': 'Phở bò tái nạm', 'qty': 2, 'price': 55000},
                {'name': 'Bia Saigon', 'qty': 1, 'price': 25000},
            ],
            'category': 'Ăn uống'
        },
        {
            'merchant': 'PETROLIMEX - CỬA HÀNG XĂG',
            'items': [
                {'name': 'Xăng RON 95', 'qty': 1, 'price': 250000},
            ],
            'category': 'Đi lại'
        },
        {
            'merchant': 'SHOPEE',
            'items': [
                {'name': 'Áo thun cotton', 'qty': 1, 'price': 185000},
            ],
            'category': 'Mua sắm'
        },
    ]
    
    sample = random.choice(samples)
    
    items = []
    total = 0
    for item in sample['items']:
        amount = item['price']
        items.append({
            'name': item['name'],
            'quantity': item['qty'],
            'unit_price': item['price'],
            'amount': amount,
            'category': sample['category']
        })
        total += amount
    
    return {
        'merchant': sample['merchant'],
        'total_amount': total,
        'timestamp': datetime.now().isoformat(),
        'category': sample['category'],
        'items': items,
        'confidence': 0.0,
        'source': 'fallback',
        'is_sample': True,
        'warnings': [
            '⚠️ Đây là dữ liệu mẫu - OCR thất bại',
            'Vui lòng nhập/sửa lại thông tin cho đúng'
        ]
    }
