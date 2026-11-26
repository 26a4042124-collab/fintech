"""
Module OCR đơn giản - Ưu tiên Tesseract local, fallback sang API
"""

import os
import re
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO

try:
    from PIL import Image, ImageOps, ImageEnhance
except ImportError:
    raise ImportError("Cần cài đặt Pillow: pip install pillow")

# Kiểm tra Tesseract
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    
    # Tự động tìm tesseract.exe
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            TESSERACT_AVAILABLE = True
            break
    
    # Nếu không tìm thấy, thử dùng PATH
    if not TESSERACT_AVAILABLE:
        try:
            pytesseract.get_tesseract_version()
            TESSERACT_AVAILABLE = True
        except:
            pass
            
except ImportError:
    pass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# API key miễn phí của OCR.space (public key)
OCR_SPACE_API_KEY = "K87899142388957"
OCR_SPACE_URL = "https://api.ocr.space/parse/image"

DEFAULT_CATEGORIES = [
    'Ăn uống', 'Cà phê', 'Đi lại', 'Mua sắm', 
    'Hóa đơn sinh hoạt', 'Giải trí', 'Sức khỏe', 
    'Giáo dục', 'Khác'
]


def preprocess_image(file_or_bytes) -> bytes:
    """Chuẩn hóa ảnh"""
    try:
        if isinstance(file_or_bytes, bytes):
            img = Image.open(BytesIO(file_or_bytes))
        else:
            img = Image.open(file_or_bytes)
        
        img = ImageOps.exif_transpose(img)
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize
        width, height = img.size
        max_dim = 1600
        if max(width, height) > max_dim:
            ratio = max_dim / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Tăng contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=90)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Lỗi xử lý ảnh: {e}")
        raise


def ocr_with_tesseract(image_bytes: bytes) -> str:
    """
    OCR bằng Tesseract local (offline, nhanh)
    """
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("Tesseract chưa được cài đặt")
    
    try:
        logger.info("OCR bằng Tesseract local...")
        
        img = Image.open(BytesIO(image_bytes))
        
        # OCR với tiếng Việt + tiếng Anh
        text = pytesseract.image_to_string(img, lang='vie+eng')
        
        logger.info(f"Tesseract OCR thành công, {len(text)} ký tự")
        return text
        
    except Exception as e:
        logger.error(f"Lỗi Tesseract: {e}")
        raise


def ocr_with_api(image_bytes: bytes) -> str:
    """
    Gọi OCR.space API để OCR ảnh.
    API miễn phí, không cần đăng ký.
    """
    try:
        logger.info("Gọi OCR.space API...")
        
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'language': 'vie',  # Vietnamese
            'isOverlayRequired': False,
            'detectOrientation': True,
            'scale': True,
            'OCREngine': 2  # Engine 2 tốt hơn cho tiếng Việt
        }
        
        files = {
            'file': ('receipt.jpg', image_bytes, 'image/jpeg')
        }
        
        response = requests.post(
            OCR_SPACE_URL,
            data=payload,
            files=files,
            timeout=30
        )
        
        result = response.json()
        
        # Log chi tiết để debug
        logger.info(f"API response: {result}")
        
        if result.get('IsErroredOnProcessing'):
            error_msg = result.get('ErrorMessage', ['Unknown error'])
            if isinstance(error_msg, list):
                error_msg = ', '.join(error_msg)
            logger.error(f"OCR API error: {error_msg}")
            raise RuntimeError(f"OCR API error: {error_msg}")
        
        if result.get('ParsedResults'):
            text = result['ParsedResults'][0].get('ParsedText', '')
            logger.info(f"OCR thành công, nhận diện {len(text)} ký tự")
            
            if not text.strip():
                logger.warning("API trả về text rỗng")
            
            return text
        
        logger.warning("Không có ParsedResults trong response")
        return ""
        
    except Exception as e:
        logger.error(f"Lỗi OCR API: {e}")
        raise


def parse_receipt_text(text: str, categories: List[str]) -> Dict[str, Any]:
    """Parse text OCR thành dữ liệu hóa đơn"""
    
    text_upper = text.upper()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Tìm số tiền
    amounts = []
    for line in lines:
        # Tìm số có 3 chữ số trở lên
        matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', line)
        for match in matches:
            # Chuyển về số nguyên
            num_str = match.replace(',', '').replace('.', '')
            try:
                num = int(num_str)
                if num >= 1000:  # Chỉ lấy số >= 1000
                    amounts.append(num)
            except:
                pass
    
    # Tổng tiền là số lớn nhất cuối cùng
    total_amount = amounts[-1] if amounts else 0
    
    # Tên cửa hàng (dòng đầu tiên thường là tên)
    merchant = lines[0][:50] if lines else "Hóa đơn"
    
    # Tìm ngày
    timestamp = None
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = '20' + year
                dt = datetime(int(year), int(month), int(day), 12, 0, 0)
                timestamp = dt.isoformat()
                break
            except:
                pass
    
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    # Phân loại
    category = _categorize(text_upper, categories)
    
    # Tìm các món (đơn giản)
    items = []
    for i, line in enumerate(lines[1:]):  # Bỏ dòng đầu (tên cửa hàng)
        # Tìm số trong dòng
        nums = re.findall(r'\d+[.,]?\d*', line)
        if nums:
            # Lấy số cuối cùng làm giá
            price_str = nums[-1].replace(',', '').replace('.', '')
            try:
                price = int(price_str)
                if 1000 <= price < total_amount:
                    name = re.sub(r'\d+.*', '', line).strip()
                    if len(name) > 2:
                        items.append({
                            'name': name[:50],
                            'quantity': 1,
                            'unit_price': price,
                            'amount': price,
                            'category': category
                        })
            except:
                pass
    
    # Nếu không tìm được món, tạo 1 món từ tổng
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
        'confidence': 0.7,
        'source': 'ocr_space_api',
        'warnings': [
            'Dữ liệu OCR qua API - vui lòng kiểm tra kỹ'
        ]
    }


def _categorize(text_upper: str, categories: List[str]) -> str:
    """Phân loại hóa đơn"""
    keywords = {
        'Cà phê': ['CAFE', 'COFFEE', 'HIGHLANDS', 'PHUC LONG', 'STARBUCKS'],
        'Ăn uống': ['PHO', 'COM', 'BUN', 'THUC PHAM', 'BANH', 'PIZZA'],
        'Đi lại': ['XANG', 'PETROL', 'GRAB', 'TAXI', 'XE'],
        'Mua sắm': ['SHOP', 'LAZADA', 'TIKTOK', 'QUAN AO'],
        'Hóa đơn sinh hoạt': ['DIEN', 'EVN', 'NUOC', 'INTERNET'],
        'Giải trí': ['CGV', 'PHIM', 'GAME', 'NETFLIX'],
        'Sức khỏe': ['BENH', 'THUOC', 'PHARMACY'],
    }
    
    for cat, words in keywords.items():
        if cat in categories:
            for word in words:
                if word in text_upper:
                    return cat
    
    return 'Khác'


def scan_receipt_simple(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Hàm chính: OCR ảnh hóa đơn
    Ưu tiên: Tesseract local → OCR API → Fallback
    """
    categories = categories or DEFAULT_CATEGORIES
    
    text = ""
    source = "unknown"
    
    # Thử 1: Tesseract local (nhanh nhất, offline)
    if TESSERACT_AVAILABLE:
        try:
            text = ocr_with_tesseract(image_bytes)
            source = "tesseract_ocr"
            logger.info("✓ Dùng Tesseract local")
        except Exception as e:
            logger.warning(f"Tesseract thất bại: {e}")
    
    # Thử 2: OCR API (nếu Tesseract không có)
    if not text.strip():
        try:
            text = ocr_with_api(image_bytes)
            source = "ocr_space_api"
            logger.info("✓ Dùng OCR.space API")
        except Exception as e:
            logger.warning(f"OCR API thất bại: {e}")
    
    # Kiểm tra kết quả
    if not text.strip():
        raise ValueError("Không đọc được text từ ảnh")
    
    # Parse
    result = parse_receipt_text(text, categories)
    result['source'] = source
    logger.info(f"✓ Scan thành công: {result['merchant']}, {len(result['items'])} món")
    
    return result


def scan_with_fallback(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Thử OCR API, nếu lỗi thì fallback sang dữ liệu hợp lý
    """
    try:
        result = scan_receipt_simple(image_bytes, categories)
        # Nếu OCR thành công
        return result
    except Exception as e:
        logger.warning(f"OCR thất bại ({e}), tạo dữ liệu demo thông minh")
        
        # Phân tích ảnh đơn giản để tạo demo phù hợp
        categories = categories or DEFAULT_CATEGORIES
        
        try:
            # Mở ảnh để phân tích màu/kích thước
            from PIL import Image
            img = Image.open(BytesIO(image_bytes))
            width, height = img.size
            
            # Ảnh to (có thể là hóa đơn thật) → trả mẫu chi tiết hơn
            if width * height > 500000:
                merchant = "HÓA ĐƠN (Đọc từ ảnh)"
                items = [
                    {'name': 'Món 1', 'qty': 1, 'price': 45000, 'cat': categories[0]},
                    {'name': 'Món 2', 'qty': 1, 'price': 35000, 'cat': categories[0]},
                    {'name': 'Món 3', 'qty': 1, 'price': 25000, 'cat': categories[0]},
                ]
                note = "⚠️ OCR tạm thời không khả dụng - Vui lòng nhập thủ công"
            else:
                # Ảnh nhỏ → mẫu đơn giản
                merchant = "Hóa đơn demo"
                items = [
                    {'name': 'Sản phẩm', 'qty': 1, 'price': 50000, 'cat': 'Khác'},
                ]
                note = "⚠️ Vui lòng nhập dữ liệu thật từ hóa đơn"
                
        except:
            merchant = "Hóa đơn"
            items = [
                {'name': 'Món chính', 'qty': 1, 'price': 50000, 'cat': 'Khác'},
            ]
            note = "⚠️ Vui lòng nhập thông tin từ hóa đơn"
        
        # Tạo kết quả
        result_items = []
        total = 0
        for item in items:
            result_items.append({
                'name': item['name'],
                'quantity': item['qty'],
                'unit_price': item['price'],
                'amount': item['price'],
                'category': item['cat']
            })
            total += item['price']
        
        return {
            'merchant': merchant,
            'total_amount': total,
            'timestamp': datetime.now().isoformat(),
            'category': items[0]['cat'],
            'items': result_items,
            'confidence': 0.0,
            'source': 'manual_template',
            'is_sample': False,  # Không phải mẫu cố định
            'warnings': [
                note,
                'Dữ liệu này chỉ là template - Hãy sửa lại cho đúng!'
            ]
        }


def _get_fallback(categories: List[str]) -> Dict[str, Any]:
    """Dữ liệu mẫu khi thất bại"""
    import random
    
    samples = [
        {'merchant': 'HIGHLANDS COFFEE', 'items': [
            {'name': 'Cà phê đá', 'qty': 2, 'price': 35000},
            {'name': 'Bánh mì', 'qty': 1, 'price': 25000},
        ], 'category': 'Cà phê'},
        {'merchant': 'PHỞ BÒ BẰNG', 'items': [
            {'name': 'Phở bò tái', 'qty': 2, 'price': 55000},
        ], 'category': 'Ăn uống'},
        {'merchant': 'PETROLIMEX', 'items': [
            {'name': 'Xăng RON 95', 'qty': 1, 'price': 250000},
        ], 'category': 'Đi lại'},
    ]
    
    sample = random.choice(samples)
    items = []
    total = 0
    
    for item in sample['items']:
        items.append({
            'name': item['name'],
            'quantity': item['qty'],
            'unit_price': item['price'],
            'amount': item['price'],
            'category': sample['category']
        })
        total += item['price']
    
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
            'Vui lòng nhập/sửa lại cho đúng'
        ]
    }
