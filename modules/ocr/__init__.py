"""
OCR Module for FinLab - Receipt Scanner
Hỗ trợ nhiều OCR engines: Tesseract, EasyOCR, OCR.space API
"""

# Import từ simple_ocr (Tesseract + OCR.space API)
from .simple_ocr import (
    preprocess_image,
    scan_with_fallback,
    scan_receipt_simple,
    ocr_with_tesseract,
    ocr_with_api,
    ReceiptProcessingError,
    TESSERACT_AVAILABLE,
    DEFAULT_CATEGORIES
)

# Import từ easyocr_scanner (EasyOCR - optional)
try:
    from .easyocr_scanner import (
        scan_receipt_easyocr,
        get_ocr_reader,
        EASYOCR_AVAILABLE
    )
except ImportError:
    EASYOCR_AVAILABLE = False
    scan_receipt_easyocr = None
    get_ocr_reader = None

__all__ = [
    'preprocess_image',
    'scan_with_fallback',
    'scan_receipt_simple',
    'ocr_with_tesseract',
    'ocr_with_api',
    'ReceiptProcessingError',
    'TESSERACT_AVAILABLE',
    'DEFAULT_CATEGORIES',
    'EASYOCR_AVAILABLE',
    'scan_receipt_easyocr',
    'get_ocr_reader'
]
