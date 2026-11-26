"""
Test module ocr_scanner.py
"""

import pytest
from io import BytesIO
from PIL import Image
from modules.ocr_scanner import (
    preprocess_image,
    normalize_and_validate,
    _parse_amount,
    fallback_scan,
    scan_with_fallback,
    ReceiptProcessingError
)


def create_test_image(width=800, height=600, color=(255, 255, 255)):
    """Tạo ảnh test đơn giản"""
    img = Image.new('RGB', (width, height), color)
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()


class TestPreprocessImage:
    """Test chuẩn hóa ảnh"""
    
    def test_preprocess_valid_image(self):
        """Test xử lý ảnh hợp lệ"""
        img_bytes = create_test_image()
        result = preprocess_image(img_bytes)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Kiểm tra output là JPEG
        img = Image.open(BytesIO(result))
        assert img.format == 'JPEG'
    
    def test_preprocess_large_image(self):
        """Test resize ảnh quá lớn"""
        img_bytes = create_test_image(width=3000, height=2000)
        result = preprocess_image(img_bytes)
        
        img = Image.open(BytesIO(result))
        assert max(img.size) <= 1600
    
    def test_preprocess_png_with_alpha(self):
        """Test xử lý PNG có alpha channel"""
        img = Image.new('RGBA', (800, 600), (255, 255, 255, 128))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        result = preprocess_image(buffer.getvalue())
        
        img_result = Image.open(BytesIO(result))
        assert img_result.mode == 'RGB'
        assert img_result.format == 'JPEG'
    
    def test_preprocess_invalid_image(self):
        """Test ảnh bị hỏng"""
        with pytest.raises(ReceiptProcessingError):
            preprocess_image(b'not an image')


class TestParseAmount:
    """Test parse số tiền VND"""
    
    def test_parse_integer(self):
        assert _parse_amount(45000) == 45000
        assert _parse_amount(125000) == 125000
    
    def test_parse_float(self):
        assert _parse_amount(45000.5) == 45000
        assert _parse_amount(125000.99) == 125000
    
    def test_parse_string_clean(self):
        assert _parse_amount("45000") == 45000
        assert _parse_amount("125000") == 125000
    
    def test_parse_string_with_separators(self):
        assert _parse_amount("45.000") == 45000
        assert _parse_amount("45,000") == 45000
        assert _parse_amount("125.000đ") == 125000
        assert _parse_amount("125,000 VND") == 125000
    
    def test_parse_invalid(self):
        assert _parse_amount("abc") == 0
        assert _parse_amount("") == 0
        assert _parse_amount(None) == 0


class TestNormalizeAndValidate:
    """Test chuẩn hóa và validate dữ liệu"""
    
    def test_normalize_valid_data(self):
        raw = {
            'merchant': 'Quán Cà Phê',
            'total_amount': 45000,
            'timestamp': '2024-01-15T10:30:00',
            'category': 'Cà phê',
            'items': [
                {
                    'name': 'Cà phê đá',
                    'quantity': 1,
                    'unit_price': 25000,
                    'amount': 25000,
                    'category': 'Cà phê'
                },
                {
                    'name': 'Bánh mì',
                    'quantity': 1,
                    'unit_price': 20000,
                    'amount': 20000,
                    'category': 'Ăn uống'
                }
            ],
            'confidence': 0.95,
            'source': 'gemini'
        }
        
        result = normalize_and_validate(raw)
        
        assert result['merchant'] == 'Quán Cà Phê'
        assert result['total_amount'] == 45000
        assert result['timestamp'] == '2024-01-15T10:30:00'
        assert len(result['items']) == 2
        assert result['confidence'] == 0.95
        assert result['source'] == 'gemini'
        assert len(result['warnings']) == 0
    
    def test_normalize_with_amount_mismatch(self):
        """Test phát hiện lệch tổng tiền"""
        raw = {
            'total_amount': 100000,
            'items': [
                {'name': 'Item 1', 'amount': 30000, 'quantity': 1, 'unit_price': 30000, 'category': 'Khác'},
                {'name': 'Item 2', 'amount': 40000, 'quantity': 1, 'unit_price': 40000, 'category': 'Khác'}
            ],
            'confidence': 0.8
        }
        
        result = normalize_and_validate(raw)
        
        # Tổng items = 70k, total = 100k -> nên có warning
        assert len(result['warnings']) > 0
        assert any('lệch' in w.lower() or 'khác' in w.lower() for w in result['warnings'])
    
    def test_normalize_future_timestamp(self):
        """Test phát hiện ngày ở tương lai"""
        raw = {
            'total_amount': 50000,
            'timestamp': '2099-01-01T00:00:00',
            'items': [],
            'confidence': 0.5
        }
        
        result = normalize_and_validate(raw)
        
        assert result['timestamp'] is None
        assert any('tương lai' in w.lower() for w in result['warnings'])
    
    def test_normalize_invalid_timestamp(self):
        """Test timestamp không hợp lệ"""
        raw = {
            'total_amount': 50000,
            'timestamp': 'invalid-date',
            'items': [],
            'confidence': 0.5
        }
        
        result = normalize_and_validate(raw)
        
        assert result['timestamp'] is None
        assert len(result['warnings']) > 0


class TestFallbackScan:
    """Test fallback mode"""
    
    def test_fallback_returns_sample_data(self):
        """Test trả dữ liệu mẫu"""
        result = fallback_scan(reason="Test mode")
        
        assert result['source'] == 'fallback'
        assert result['is_sample'] is True
        assert result['merchant'] is not None
        assert result['total_amount'] > 0
        assert len(result['items']) > 0
        assert result['confidence'] == 0.0
        assert len(result['warnings']) > 0
    
    def test_fallback_includes_reason(self):
        """Test lý do fallback được ghi trong warnings"""
        reason = "Không có API key"
        result = fallback_scan(reason=reason)
        
        warnings_text = ' '.join(result['warnings'])
        assert reason in warnings_text


class TestScanWithFallback:
    """Test hàm điều phối chính"""
    
    def test_scan_without_api_key(self, monkeypatch):
        """Test fallback khi không có API key"""
        # Mock không có GEMINI_API_KEY
        import modules.ocr_scanner as ocr_module
        monkeypatch.setattr(ocr_module, 'GEMINI_API_KEY', None)
        
        img_bytes = create_test_image()
        result = scan_with_fallback(img_bytes)
        
        assert result['source'] == 'fallback'
        assert result['is_sample'] is True
    
    def test_scan_without_gemini_library(self, monkeypatch):
        """Test fallback khi không có thư viện Gemini"""
        import modules.ocr_scanner as ocr_module
        monkeypatch.setattr(ocr_module, 'GEMINI_AVAILABLE', False)
        
        img_bytes = create_test_image()
        result = scan_with_fallback(img_bytes)
        
        assert result['source'] == 'fallback'
        warnings_text = ' '.join(result['warnings'])
        assert 'thư viện' in warnings_text.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
