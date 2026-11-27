"""
Module OCR đơn giản - Ưu tiên Tesseract local, fallback sang API
Enhanced với Image Preprocessing nâng cao và Information Extraction thông minh
"""

import os
import re
import logging
import requests
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    import cv2
except ImportError:
    raise ImportError("Cần cài đặt Pillow và OpenCV: pip install pillow opencv-python")


class ReceiptProcessingError(Exception):
    """Lỗi xử lý ảnh hóa đơn"""
    pass

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

# Keywords để phát hiện các trường thông tin
MERCHANT_KEYWORDS = ['CÔNG TY', 'RESTAURANT', 'COFFEE', 'SHOP', 'STORE', 'CAFE']
TOTAL_KEYWORDS = ['TỔNG', 'TOTAL', 'THANH TOÁN', 'TO PAY', 'AMOUNT DUE', 'SUM', 'CỘNG']
SUBTOTAL_KEYWORDS = ['SUBTOTAL', 'TIỀN HÀNG', 'TẠM TÍNH']
TAX_KEYWORDS = ['VAT', 'THUẾ', 'TAX']
DISCOUNT_KEYWORDS = ['GIẢM GIÁ', 'DISCOUNT', 'KHUYẾN MÃI', 'PROMOTION']
HEADER_KEYWORDS = ['HÓA ĐƠN', 'INVOICE', 'RECEIPT', 'BILL', 'PHIẾU']


def assess_image_quality(img_array: np.ndarray) -> Dict[str, Any]:
    """
    Đánh giá chất lượng ảnh để quyết định preprocessing phù hợp.
    
    Returns:
        dict: {'brightness': float, 'sharpness': float, 'is_good': bool}
    """
    # Chuyển sang grayscale để đánh giá
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Đánh giá độ sáng (0-255)
    brightness = np.mean(gray)
    
    # Đánh giá độ nét (Laplacian variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    
    # Đánh giá tổng thể
    is_dark = brightness < 90
    is_bright = brightness > 200
    is_blurry = sharpness < 100
    is_good = not (is_dark or is_bright or is_blurry)
    
    return {
        'brightness': float(brightness),
        'sharpness': float(sharpness),
        'is_dark': is_dark,
        'is_bright': is_bright,
        'is_blurry': is_blurry,
        'is_good': is_good
    }


def adaptive_preprocess(img: Image.Image, quality_info: Dict) -> Image.Image:
    """
    Áp dụng preprocessing thích ứng dựa trên chất lượng ảnh.
    
    Args:
        img: PIL Image
        quality_info: Thông tin chất lượng từ assess_image_quality
        
    Returns:
        PIL Image đã xử lý
    """
    # Chuyển sang numpy array để xử lý với OpenCV
    img_array = np.array(img)
    
    # 1. Grayscale conversion (tốt cho OCR)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # 2. Denoising (giảm nhiễu)
    if quality_info.get('is_blurry', False):
        # Nếu ảnh mờ, dùng denoising nhẹ
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Cải thiện contrast cục bộ
    if quality_info.get('is_dark', False) or quality_info.get('is_bright', False):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    
    # 4. Adaptive Thresholding (tách text khỏi background)
    # Binary image tốt hơn cho OCR
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2
    )
    
    # 5. Morphological operations (làm rõ cấu trúc text)
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 6. Sharpen (làm nét chữ)
    if quality_info.get('is_blurry', False):
        kernel_sharpen = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
        binary = cv2.filter2D(binary, -1, kernel_sharpen)
    
    # Chuyển về PIL Image
    img_processed = Image.fromarray(binary)
    
    return img_processed


def preprocess_image(file_or_bytes, mode='balanced') -> bytes:
    """
    Chuẩn hóa ảnh với preprocessing nâng cao.
    
    Args:
        file_or_bytes: File object hoặc bytes
        mode: 'light' (preprocessing nhẹ), 'balanced' (cân bằng), 'aggressive' (mạnh)
        
    Returns:
        bytes: Ảnh đã xử lý (JPEG)
    """
    try:
        # 1. Mở ảnh
        if isinstance(file_or_bytes, bytes):
            img = Image.open(BytesIO(file_or_bytes))
        else:
            img = Image.open(file_or_bytes)
        
        # 2. EXIF rotation
        img = ImageOps.exif_transpose(img)
        
        # 3. RGB conversion
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 4. Resize nếu quá lớn
        width, height = img.size
        max_dim = 2000
        if max(width, height) > max_dim:
            ratio = max_dim / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized from {width}x{height} to {new_size[0]}x{new_size[1]}")
        
        # 5. Áp dụng preprocessing dựa theo mode
        if mode == 'light':
            # Chỉ tăng nhẹ contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)
            
        elif mode == 'balanced':
            # Đánh giá chất lượng và preprocessing thích ứng nhẹ
            img_array = np.array(img)
            quality_info = assess_image_quality(img_array)
            
            logger.info(f"Image quality: brightness={quality_info['brightness']:.1f}, "
                       f"sharpness={quality_info['sharpness']:.1f}")
            
            # Chỉ áp dụng khi cần thiết
            if quality_info.get('is_dark'):
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.3)
            elif quality_info.get('is_bright'):
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(0.9)
            
            # Tăng contrast vừa phải
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.4)
            
            # Sharpen nếu mờ
            if quality_info.get('is_blurry'):
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)
        
        elif mode == 'aggressive':
            # Full preprocessing với OpenCV
            img_array = np.array(img)
            quality_info = assess_image_quality(img_array)
            img = adaptive_preprocess(img, quality_info)
        
        # 6. Nén JPEG
        output = BytesIO()
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Lỗi xử lý ảnh: {e}")
        raise


def ocr_with_tesseract(image_bytes: bytes) -> Tuple[str, List[Dict]]:
    """
    OCR bằng Tesseract local (offline, nhanh) với confidence scores.
    
    Returns:
        Tuple[str, List[Dict]]: (full_text, word_data)
            word_data: [{'text': str, 'conf': float, 'left': int, 'top': int, 'width': int, 'height': int}]
    """
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("Tesseract chưa được cài đặt")
    
    try:
        logger.info("OCR bằng Tesseract local...")
        
        img = Image.open(BytesIO(image_bytes))
        
        # OCR với tiếng Việt + tiếng Anh
        # PSM 6: Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, lang='vie+eng', config=custom_config)
        
        # Lấy detailed data với confidence scores và bounding boxes
        data = pytesseract.image_to_data(img, lang='vie+eng', config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Parse word data
        word_data = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text_word = data['text'][i].strip()
            if text_word:  # Bỏ qua empty
                conf = float(data['conf'][i])
                word_data.append({
                    'text': text_word,
                    'conf': conf / 100.0,  # Normalize to 0-1
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })
        
        # Tính average confidence
        if word_data:
            avg_conf = sum(w['conf'] for w in word_data) / len(word_data)
            logger.info(f"Tesseract OCR thành công: {len(text)} chars, {len(word_data)} words, avg_conf={avg_conf:.2%}")
        else:
            logger.warning("Tesseract không nhận diện được text nào")
        
        return text, word_data
        
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


def extract_merchant_name(lines: List[str], word_data: List[Dict]) -> Tuple[str, float]:
    """
    Trích xuất tên cửa hàng thông minh.
    
    Strategy:
    1. Bỏ qua dòng header chung (HÓA ĐƠN, INVOICE, RECEIPT)
    2. Tìm dòng có font lớn nhất (thường là tên cửa hàng)
    3. Tìm dòng có chứa keywords: CÔNG TY, SHOP, CAFE, RESTAURANT
    4. Fallback: Dòng đầu tiên không phải header
    
    Returns:
        Tuple[str, float]: (merchant_name, confidence)
    """
    if not lines:
        return "Hóa đơn", 0.3
    
    # Bỏ qua dòng header
    candidate_lines = []
    for i, line in enumerate(lines[:5]):  # Chỉ xét 5 dòng đầu
        line_upper = line.upper()
        
        # Skip nếu là header chung
        is_header = any(keyword in line_upper for keyword in HEADER_KEYWORDS)
        if is_header:
            continue
        
        # Check nếu có merchant keywords
        has_merchant_keyword = any(keyword in line_upper for keyword in MERCHANT_KEYWORDS)
        
        # Tính độ dài và số chữ cái (merchant thường có nhiều chữ)
        num_letters = sum(c.isalpha() for c in line)
        
        if num_letters >= 3:  # Ít nhất 3 chữ cái
            candidate_lines.append({
                'line': line,
                'index': i,
                'has_keyword': has_merchant_keyword,
                'num_letters': num_letters
            })
    
    if not candidate_lines:
        return lines[0][:50], 0.3
    
    # Ưu tiên dòng có keyword
    for candidate in candidate_lines:
        if candidate['has_keyword']:
            return candidate['line'][:50], 0.9
    
    # Fallback: Dòng đầu tiên có nhiều chữ nhất
    best_candidate = max(candidate_lines, key=lambda x: x['num_letters'])
    return best_candidate['line'][:50], 0.6


def extract_total_amount(lines: List[str], word_data: List[Dict]) -> Tuple[int, float]:
    """
    Trích xuất tổng tiền thông minh.
    
    Strategy:
    1. Tìm dòng có keywords: TỔNG, TOTAL, THANH TOÁN
    2. Lấy số lớn nhất trong dòng đó
    3. Fallback: Số lớn nhất trong toàn bộ text (loại trừ số điện thoại)
    
    Returns:
        Tuple[int, float]: (total_amount, confidence)
    """
    all_amounts = []
    
    for i, line in enumerate(lines):
        line_upper = line.upper()
        
        # Tìm tất cả số tiền trong dòng
        # Pattern: 123,456 hoặc 123.456 hoặc 123456
        matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', line)
        
        for match in matches:
            # Chuyển về số nguyên
            num_str = match.replace(',', '').replace('.', '')
            try:
                amount = int(num_str)
                
                # Loại trừ số điện thoại (10-11 chữ số)
                if len(num_str) >= 10:
                    continue
                
                # Chỉ lấy số >= 1000 (tiền Việt ít khi < 1000đ)
                if amount < 1000:
                    continue
                
                # Check nếu dòng có total keywords
                has_total_keyword = any(keyword in line_upper for keyword in TOTAL_KEYWORDS)
                has_subtotal_keyword = any(keyword in line_upper for keyword in SUBTOTAL_KEYWORDS)
                
                # Confidence cao nếu có keyword TỔNG
                if has_total_keyword:
                    return amount, 0.95
                elif has_subtotal_keyword:
                    # Subtotal có thể là tổng nếu không tìm thấy total
                    all_amounts.append({'amount': amount, 'conf': 0.7, 'line_idx': i})
                else:
                    all_amounts.append({'amount': amount, 'conf': 0.4, 'line_idx': i})
                    
            except ValueError:
                pass
    
    if not all_amounts:
        return 0, 0.1
    
    # Ưu tiên số ở cuối hóa đơn (total thường ở cuối)
    # Sort theo confidence và vị trí
    all_amounts.sort(key=lambda x: (x['conf'], x['line_idx']), reverse=True)
    
    best = all_amounts[0]
    return best['amount'], best['conf']


def extract_transaction_date(text: str) -> Tuple[Optional[str], float]:
    """
    Trích xuất ngày giao dịch.
    
    Returns:
        Tuple[Optional[str], float]: (iso_datetime, confidence)
    """
    # Nhiều patterns cho ngày tháng Việt Nam
    date_patterns = [
        # DD/MM/YYYY hoặc DD-MM-YYYY
        (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', '%d-%m-%Y', 0.9),
        # DD/MM/YY
        (r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})', '%d-%m-%y', 0.8),
        # YYYY-MM-DD (ISO format)
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d', 0.95),
    ]
    
    # Thêm pattern cho giờ:phút
    time_pattern = r'(\d{1,2}):(\d{2})(?::(\d{2}))?'
    
    best_match = None
    best_conf = 0
    
    for pattern, date_format, conf in date_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                date_str = match.group(0)
                
                # Parse ngày
                if 'y' in date_format:  # DD-MM-YY format
                    parts = re.split(r'[/-]', date_str)
                    year = int(parts[2])
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                    dt = datetime(year, int(parts[1]), int(parts[0]), 12, 0, 0)
                elif date_format == '%Y-%m-%d':
                    parts = date_str.split('-')
                    dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]), 12, 0, 0)
                else:  # DD/MM/YYYY
                    parts = re.split(r'[/-]', date_str)
                    dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]), 12, 0, 0)
                
                # Tìm giờ gần ngày này
                # Lấy 50 ký tự trước và sau ngày
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(text), match.end() + 50)
                context = text[start_pos:end_pos]
                
                time_match = re.search(time_pattern, context)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        dt = dt.replace(hour=hour, minute=minute)
                        conf += 0.05  # Bonus confidence nếu có giờ
                
                # Validate ngày không trong tương lai
                if dt > datetime.now():
                    continue
                
                # Validate ngày không quá xa (< 5 năm)
                if (datetime.now() - dt).days > 365 * 5:
                    continue
                
                if conf > best_conf:
                    best_match = dt.isoformat()
                    best_conf = conf
                    
            except (ValueError, IndexError):
                pass
    
    if best_match:
        return best_match, best_conf
    
    # Fallback: Ngày hiện tại
    return datetime.now().isoformat(), 0.2


def extract_items(lines: List[str], total_amount: int, category: str) -> List[Dict[str, Any]]:
    """
    Trích xuất danh sách món.
    
    Strategy:
    1. Tìm vùng table (các dòng có cấu trúc tương tự)
    2. Parse: Tên món | Số lượng | Đơn giá | Thành tiền
    3. Bỏ qua header table, footer
    4. Validate: giá < total, giá >= 1000
    
    Returns:
        List[Dict]: Danh sách items
    """
    items = []
    
    for i, line in enumerate(lines):
        # Bỏ qua dòng quá ngắn
        if len(line.strip()) < 3:
            continue
        
        line_upper = line.upper()
        
        # Skip header rows
        is_header_row = any(keyword in line_upper for keyword in HEADER_KEYWORDS + TOTAL_KEYWORDS + ['SL', 'SỐ LƯỢNG', 'QTY', 'QUANTITY', 'ĐƠN GIÁ', 'UNIT PRICE', 'THÀNH TIỀN', 'AMOUNT'])
        if is_header_row:
            continue
        
        # Tìm số tiền trong dòng
        amounts_in_line = re.findall(r'(\d{1,3}(?:[.,]\d{3})*)', line)
        
        if not amounts_in_line:
            continue
        
        # Parse amounts
        parsed_amounts = []
        for amt_str in amounts_in_line:
            try:
                amt = int(amt_str.replace(',', '').replace('.', ''))
                if 1000 <= amt < total_amount:  # Phải >= 1000 và < total
                    parsed_amounts.append(amt)
            except ValueError:
                pass
        
        if not parsed_amounts:
            continue
        
        # Lấy số cuối cùng làm thành tiền (convention)
        item_price = parsed_amounts[-1]
        
        # Lấy tên món (phần trước số đầu tiên)
        name_match = re.match(r'^(.+?)(?:\d)', line)
        if name_match:
            item_name = name_match.group(1).strip()
        else:
            item_name = re.sub(r'\d+.*', '', line).strip()
        
        # Validate tên món
        if len(item_name) < 2:
            continue
        
        # Tìm số lượng (thường là số nhỏ ở đầu hoặc giữa)
        quantity = 1
        if len(parsed_amounts) >= 2:
            # Nếu có nhiều số, số đầu có thể là số lượng
            if parsed_amounts[0] < 20:  # Số lượng thường < 20
                quantity = parsed_amounts[0]
        
        items.append({
            'name': item_name[:50],
            'quantity': quantity,
            'unit_price': item_price // quantity if quantity > 0 else item_price,
            'amount': item_price,
            'category': category
        })
    
    # Nếu không parse được items, tạo 1 item từ total
    if not items and total_amount > 0:
        items.append({
            'name': 'Tổng hóa đơn',
            'quantity': 1,
            'unit_price': total_amount,
            'amount': total_amount,
            'category': category
        })
    
    return items


def parse_receipt_text(text: str, categories: List[str], word_data: List[Dict] = None) -> Dict[str, Any]:
    """
    Parse text OCR thành dữ liệu hóa đơn với logic thông minh.
    
    Args:
        text: Full text từ OCR
        categories: Danh sách categories
        word_data: Word-level data với confidence và bounding boxes
        
    Returns:
        dict: Dữ liệu hóa đơn có cấu trúc
    """
    if word_data is None:
        word_data = []
    
    text_upper = text.upper()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 1. Extract merchant name
    merchant, merchant_conf = extract_merchant_name(lines, word_data)
    
    # 2. Extract total amount
    total_amount, total_conf = extract_total_amount(lines, word_data)
    
    # 3. Phân loại category
    category = _categorize(text_upper, categories)
    
    # 4. Extract transaction date
    timestamp, date_conf = extract_transaction_date(text)
    
    # 5. Extract items
    items = extract_items(lines, total_amount, category)
    
    # 6. Tính overall confidence
    # Weighted average: merchant(30%), total(40%), date(20%), items(10%)
    overall_conf = (
        merchant_conf * 0.3 +
        total_conf * 0.4 +
        date_conf * 0.2 +
        (0.8 if len(items) > 1 else 0.5) * 0.1
    )
    
    # 7. Generate warnings
    warnings = []
    if merchant_conf < 0.7:
        warnings.append(f"Độ tin cậy tên cửa hàng thấp ({merchant_conf:.0%})")
    if total_conf < 0.7:
        warnings.append(f"Độ tin cậy tổng tiền thấp ({total_conf:.0%})")
    if date_conf < 0.5:
        warnings.append(f"Không tìm thấy ngày giao dịch rõ ràng ({date_conf:.0%})")
    if len(items) == 1 and items[0]['name'] == 'Tổng hóa đơn':
        warnings.append("Không parse được món riêng lẻ, chỉ có tổng hóa đơn")
    
    # 8. Validate sum of items
    items_sum = sum(item['amount'] for item in items)
    if items_sum != total_amount and len(items) > 1:
        warnings.append(f"Tổng items ({items_sum:,}đ) khác tổng hóa đơn ({total_amount:,}đ)")
    
    return {
        'merchant': merchant,
        'total_amount': total_amount,
        'timestamp': timestamp,
        'category': category,
        'items': items,
        'confidence': overall_conf,
        'field_confidence': {
            'merchant': merchant_conf,
            'total': total_conf,
            'date': date_conf
        },
        'source': 'tesseract_ocr',
        'warnings': warnings,
        'raw_text': text[:500]  # Lưu 500 ký tự đầu để debug
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
    Hàm chính: OCR ảnh hóa đơn với multi-attempt strategy
    
    Strategy:
    1. Thử OCR trên ảnh gốc (light preprocessing)
    2. Nếu confidence thấp, thử lại với balanced preprocessing
    3. Chọn kết quả có confidence cao hơn
    """
    categories = categories or DEFAULT_CATEGORIES
    
    results = []
    
    # Attempt 1: Light preprocessing
    try:
        logger.info("=== Attempt 1: Light preprocessing ===")
        img_light = preprocess_image(BytesIO(image_bytes), mode='light')
        
        if TESSERACT_AVAILABLE:
            text, word_data = ocr_with_tesseract(img_light)
            result = parse_receipt_text(text, categories, word_data)
            result['source'] = 'tesseract_ocr_light'
            results.append(result)
            logger.info(f"Light preprocessing: confidence={result['confidence']:.0%}, "
                       f"total={result['total_amount']:,}đ")
        
    except Exception as e:
        logger.warning(f"Light preprocessing failed: {e}")
    
    # Attempt 2: Balanced preprocessing (nếu attempt 1 confidence thấp)
    if not results or results[0]['confidence'] < 0.6:
        try:
            logger.info("=== Attempt 2: Balanced preprocessing ===")
            img_balanced = preprocess_image(BytesIO(image_bytes), mode='balanced')
            
            if TESSERACT_AVAILABLE:
                text, word_data = ocr_with_tesseract(img_balanced)
                result = parse_receipt_text(text, categories, word_data)
                result['source'] = 'tesseract_ocr_balanced'
                results.append(result)
                logger.info(f"Balanced preprocessing: confidence={result['confidence']:.0%}, "
                           f"total={result['total_amount']:,}đ")
            
        except Exception as e:
            logger.warning(f"Balanced preprocessing failed: {e}")
    
    # Attempt 3: OCR.space API fallback
    if not results or all(r['total_amount'] == 0 for r in results):
        try:
            logger.info("=== Attempt 3: OCR.space API ===")
            img_light = preprocess_image(BytesIO(image_bytes), mode='light')
            text = ocr_with_api(img_light)
            result = parse_receipt_text(text, categories, [])
            result['source'] = 'ocr_space_api'
            results.append(result)
            logger.info(f"OCR.space API: confidence={result['confidence']:.0%}, "
                       f"total={result['total_amount']:,}đ")
        except Exception as e:
            logger.warning(f"OCR.space API failed: {e}")
    
    # Chọn kết quả tốt nhất
    if not results:
        raise ValueError("Không đọc được text từ ảnh sau tất cả các attempts")
    
    # Sort theo confidence và total_amount (ưu tiên có total > 0)
    results.sort(key=lambda x: (x['total_amount'] > 0, x['confidence']), reverse=True)
    best_result = results[0]
    
    logger.info(f"✓ Best result: {best_result['source']}, {best_result['merchant']}, "
               f"{best_result['total_amount']:,}đ, confidence={best_result['confidence']:.0%}, "
               f"{len(best_result['items'])} món")
    
    return best_result


def scan_with_fallback(image_bytes: bytes, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    OCR hóa đơn - Ưu tiên Tesseract → OCR.space API
    
    Theo yêu cầu: "Không được trả về thông tin hóa đơn mẫu khi chưa thực hiện nhận diện ảnh"
    Nếu OCR thất bại, raise exception thay vì trả mock data.
    
    Args:
        image_bytes: Ảnh đã chuẩn hóa
        categories: Danh sách danh mục
        
    Returns:
        dict: Dữ liệu OCR thực tế
        
    Raises:
        RuntimeError: Khi OCR không khả dụng hoặc thất bại
    """
    try:
        result = scan_receipt_simple(image_bytes, categories)
        # OCR thành công
        return result
    except Exception as e:
        logger.error(f"OCR thất bại: {e}")
        
        # Tạo thông báo lỗi chi tiết
        error_msg = "Không thể nhận diện hóa đơn.\n\n"
        
        if not TESSERACT_AVAILABLE:
            error_msg += "⚠️ Tesseract OCR chưa được cài đặt.\n"
            error_msg += "Hướng dẫn cài đặt: Xem file CAI_DAT_TESSERACT.md\n\n"
        
        error_msg += "🔧 Giải pháp:\n"
        error_msg += "1. Cài đặt Tesseract OCR để quét offline\n"
        error_msg += "2. Kiểm tra kết nối internet để dùng OCR.space API\n"
        error_msg += "3. Thử lại với ảnh rõ nét hơn\n"
        error_msg += "4. Hoặc nhập thủ công bằng form bên dưới\n\n"
        error_msg += f"Chi tiết lỗi: {str(e)}"
        
        raise RuntimeError(error_msg)



