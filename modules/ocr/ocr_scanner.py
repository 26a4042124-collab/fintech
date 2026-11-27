"""
Module quét hóa đơn bằng AI Vision (Gemini) với fallback offline.

Chức năng chính:
- Chuẩn hóa ảnh (xoay EXIF, resize, tăng độ nét)
- Gọi Gemini Vision API để bóc dữ liệu có cấu trúc
- Validate và normalize kết quả
- Fallback về dữ liệu mẫu khi không có mạng/API key
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
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Thử import local OCR (optional)
try:
    import pytesseract
    from pytesseract import Output
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Cấu hình logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Đọc cấu hình từ biến môi trường
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
MAX_IMAGE_SIZE = 1600  # px
JPEG_QUALITY = 85

# Danh sách rổ chi tiêu mặc định
DEFAULT_CATEGORIES = [
    'Ăn uống', 'Cà phê', 'Đi lại', 'Mua sắm', 
    'Hóa đơn sinh hoạt', 'Giải trí', 'Sức khỏe', 
    'Giáo dục', 'Khác'
]


class ReceiptProcessingError(Exception):
    """Lỗi xử lý ảnh hóa đơn"""
    pass


def preprocess_image(file_or_bytes) -> bytes:
    """
    Chuẩn hóa ảnh trước khi gửi API.
    
    Args:
        file_or_bytes: File object hoặc bytes của ảnh
        
    Returns:
        bytes: Ảnh JPEG đã chuẩn hóa
        
    Raises:
        ReceiptProcessingError: Khi ảnh không hợp lệ hoặc bị hỏng
    """
    try:
        # Mở ảnh
        if isinstance(file_or_bytes, bytes):
            img = Image.open(BytesIO(file_or_bytes))
        else:
            img = Image.open(file_or_bytes)
        
        # Xoay đúng chiều theo EXIF
        img = ImageOps.exif_transpose(img)
        
        # Chuyển sang RGB (xử lý PNG alpha, CMYK)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Tạo background trắng cho alpha
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize nếu quá lớn (giữ tỉ lệ)
        width, height = img.size
        if max(width, height) > MAX_IMAGE_SIZE:
            ratio = MAX_IMAGE_SIZE / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Đã resize ảnh từ {width}x{height} xuống {new_size[0]}x{new_size[1]}")
        
        # Tăng nhẹ độ tương phản và độ nét
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)
        
        # Nén JPEG
        output = BytesIO()
        img.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Lỗi xử lý ảnh: {str(e)}")
        raise ReceiptProcessingError(f"Không thể xử lý ảnh: {str(e)}")


def scan_receipt(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Quét hóa đơn bằng Gemini Vision API.
    
    Args:
        image_bytes: Ảnh đã chuẩn hóa (JPEG bytes)
        categories: Danh sách rổ chi tiêu được phép
        
    Returns:
        dict: Dữ liệu hóa đơn có cấu trúc
        
    Raises:
        Exception: Khi gọi API thất bại
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("Thiếu thư viện google-generativeai")
    
    if not GEMINI_API_KEY:
        raise ValueError("Thiếu GEMINI_API_KEY trong biến môi trường")
    
    categories = categories or DEFAULT_CATEGORIES
    
    # Cấu hình Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Tạo prompt tiếng Việt rõ ràng
    prompt = f"""Bạn là trợ lý AI chuyên đọc hóa đơn tại Việt Nam.

Phân tích ảnh hóa đơn này và trả về JSON thuần theo CHÍNH XÁC schema sau:

{{
  "merchant": "Tên cửa hàng hoặc null nếu không đọc được",
  "total_amount": 0,
  "timestamp": "YYYY-MM-DDTHH:MM:SS hoặc null",
  "category": "Một trong các rổ: {', '.join(categories)}",
  "items": [
    {{"name": "Tên món", "quantity": 1, "unit_price": 0, "amount": 0, "category": "Rổ chi tiêu"}}
  ],
  "confidence": 0.95,
  "source": "gemini"
}}

QUY TẮC QUAN TRỌNG:
1. Số tiền PHẢI là số nguyên VND, KHÔNG có dấu phân cách (ví dụ: 45000 thay vì "45.000")
2. Nếu không đọc được trường nào, trả null - KHÔNG được bịa
3. Ngày giờ theo ISO 8601, nếu chỉ có ngày thì thêm thời gian 12:00:00
4. category PHẢI nằm trong danh sách: {', '.join(categories)}
5. Nếu category không rõ hoặc không khớp, dùng "Khác"
6. Với từng items, chọn category phù hợp nhất
7. KHÔNG thêm bất kỳ text nào ngoài JSON
8. confidence là độ tin cậy từ 0.0 đến 1.0

Hãy phân tích hóa đơn và trả về JSON:"""
    
    try:
        # Gọi API với timeout và retry
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Upload ảnh
        img_part = {
            'mime_type': 'image/jpeg',
            'data': image_bytes
        }
        
        # Gọi API với temperature thấp để kết quả ổn định
        response = model.generate_content(
            [prompt, img_part],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
            request_options={'timeout': 20}
        )
        
        # Parse JSON từ response
        result_text = response.text.strip()
        
        # Loại bỏ markdown code fence nếu có
        if result_text.startswith('```'):
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
        
        import json
        result = json.loads(result_text)
        
        logger.info(f"Gemini scan thành công: {result.get('merchant', 'N/A')}, "
                   f"{len(result.get('items', []))} món, confidence {result.get('confidence', 0)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Lỗi gọi Gemini API: {str(e)}")
        raise


def normalize_and_validate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hóa và kiểm tra tính hợp lệ của dữ liệu từ API.
    
    Args:
        raw: Dữ liệu thô từ Gemini
        
    Returns:
        dict: Dữ liệu đã chuẩn hóa với danh sách warnings
    """
    warnings = []
    
    # Ép kiểu số tiền
    try:
        total_amount = _parse_amount(raw.get('total_amount', 0))
    except Exception:
        total_amount = 0
        warnings.append("Không đọc được tổng tiền, đặt về 0")
    
    # Parse timestamp
    timestamp = raw.get('timestamp')
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Kiểm tra không ở tương lai
            if dt > datetime.now():
                warnings.append("Ngày giao dịch ở tương lai, vui lòng kiểm tra lại")
                timestamp = None
        except Exception:
            warnings.append("Ngày giờ không đúng định dạng")
            timestamp = None
    
    # Chuẩn hóa items
    items = []
    items_sum = 0
    for item in raw.get('items', []):
        try:
            amount = _parse_amount(item.get('amount', 0))
            items.append({
                'name': str(item.get('name', 'Không rõ')),
                'quantity': int(item.get('quantity', 1)),
                'unit_price': _parse_amount(item.get('unit_price', 0)),
                'amount': amount,
                'category': str(item.get('category', 'Khác'))
            })
            items_sum += amount
        except Exception as e:
            logger.warning(f"Bỏ qua item không hợp lệ: {e}")
    
    # Kiểm tra lệch tổng
    if items_sum > 0 and total_amount > 0:
        diff_pct = abs(items_sum - total_amount) / total_amount * 100
        if diff_pct > 5:  # Lệch > 5%
            warnings.append(f"Tổng các món ({items_sum:,}đ) khác tổng hóa đơn ({total_amount:,}đ)")
    
    result = {
        'merchant': raw.get('merchant'),
        'total_amount': total_amount,
        'timestamp': timestamp,
        'category': raw.get('category', 'Khác'),
        'items': items,
        'confidence': float(raw.get('confidence', 0.5)),
        'source': raw.get('source', 'gemini'),
        'warnings': warnings
    }
    
    return result


def _parse_amount(value: Any) -> int:
    """Parse số tiền từ nhiều định dạng về int VND"""
    if isinstance(value, (int, float)):
        return int(value)
    
    if isinstance(value, str):
        # Loại bỏ các ký tự không phải số
        clean = re.sub(r'[^\d]', '', value)
        return int(clean) if clean else 0
    
    return 0


def fallback_scan(image_bytes: Optional[bytes] = None, reason: str = "") -> Dict[str, Any]:
    """
    Trả dữ liệu mẫu khi không thể quét thật.
    Hoặc thử dùng Tesseract OCR local nếu có.
    
    Args:
        image_bytes: Ảnh (có thể dùng để OCR local)
        reason: Lý do fallback
        
    Returns:
        dict: Dữ liệu hóa đơn mẫu với cảnh báo rõ ràng
    """
    logger.warning(f"Fallback được kích hoạt: {reason}")
    
    # Thử dùng Tesseract local OCR nếu có
    if image_bytes and TESSERACT_AVAILABLE:
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(image_bytes))
            # Dùng Tesseract để OCR
            text = pytesseract.image_to_string(img, lang='vie+eng')
            
            # Parse dữ liệu đơn giản từ text
            import re
            amounts = re.findall(r'\d{3,}\s*(?:đ|VND)?', text, re.IGNORECASE)
            
            if amounts:
                logger.info(f"Local OCR nhận diện được {len(amounts)} số tiền")
                return {
                    'merchant': 'Hóa đơn (OCR local)',
                    'total_amount': _parse_amount(amounts[-1]) if amounts else 0,
                    'timestamp': datetime.now().isoformat(),
                    'category': 'Khác',
                    'items': [
                        {
                            'name': 'Món 1',
                            'quantity': 1,
                            'unit_price': _parse_amount(amounts[-1]) if amounts else 0,
                            'amount': _parse_amount(amounts[-1]) if amounts else 0,
                            'category': 'Khác'
                        }
                    ],
                    'confidence': 0.5,
                    'source': 'local_ocr',
                    'warnings': [
                        '⚠️ Sử dụng OCR cục bộ (độ tin cậy thấp)',
                        'Vui lòng kiểm tra kỹ dữ liệu trước khi lưu'
                    ]
                }
        except Exception as e:
            logger.warning(f"Local OCR thất bại: {e}")
    
    # Fallback về dữ liệu mẫu - đa dạng hơn để demo tốt
    now = datetime.now().isoformat()
    
    # Các mẫu hóa đơn khác nhau để demo đa dạng
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
                {'name': 'Nước chấm', 'qty': 2, 'price': 0},
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
            'merchant': 'SHOPEE / LAZADA',
            'items': [
                {'name': 'Áo thun cotton', 'qty': 1, 'price': 185000},
                {'name': 'Phí vận chuyển', 'qty': 1, 'price': 0},
            ],
            'category': 'Mua sắm'
        },
        {
            'merchant': 'EVN - ĐIỆN LỰC',
            'items': [
                {'name': 'Tiền điện 09/2026', 'qty': 1, 'price': 850000},
            ],
            'category': 'Hóa đơn sinh hoạt'
        }
    ]
    
    # Chọn mẫu ngẫu nhiên
    import random
    sample = random.choice(samples)
    
    items = []
    total = 0
    for item in sample['items']:
        amount = item['price'] if item['price'] > 0 else 0
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
        'timestamp': now,
        'category': sample['category'],
        'items': items,
        'confidence': 0.0,
        'source': 'fallback',
        'is_sample': True,
        'warnings': [
            '⚠️ ĐÂY LÀ DỮ LIỆU MẪU DEMO, KHÔNG PHẢI NỘI DUNG THẬT!',
            f'Lý do: {reason}',
            'Vui lòng nhập/sửa lại thông tin cho đúng hoặc thử API key Gemini.'
        ]
    }


def scan_with_fallback(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Hàm điều phối chính: Thử Gemini, lỗi thì fallback.
    Luôn trả về dict hợp lệ, không bao giờ raise exception.
    
    Args:
        image_bytes: Ảnh đã chuẩn hóa
        categories: Danh sách rổ chi tiêu
        
    Returns:
        dict: Dữ liệu hóa đơn (thật hoặc mẫu)
    """
    # Kiểm tra điều kiện cơ bản
    if not GEMINI_AVAILABLE:
        return fallback_scan(image_bytes, "Chưa cài đặt thư viện google-generativeai")
    
    if not GEMINI_API_KEY:
        return fallback_scan(image_bytes, "Thiếu GEMINI_API_KEY trong cấu hình")
    
    # Thử quét bằng Gemini
    try:
        raw_result = scan_receipt(image_bytes, categories)
        normalized = normalize_and_validate(raw_result)
        return normalized
        
    except Exception as e:
        logger.error(f"Scan thất bại, chuyển sang fallback: {str(e)}")
        
        # Phân loại lý do để hiển thị message rõ ràng
        reason = "Không thể kết nối dịch vụ AI"
        if "timeout" in str(e).lower():
            reason = "Hết thời gian chờ kết nối API"
        elif "api" in str(e).lower() or "key" in str(e).lower():
            reason = "Lỗi xác thực API key"
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            reason = "Đã hết quota API miễn phí"
        
        return fallback_scan(image_bytes, reason)
