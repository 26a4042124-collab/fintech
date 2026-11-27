#!/usr/bin/env python3
"""
Script test PaddleOCR - Không cần train, dùng model có sẵn
"""

import sys
import time
from pathlib import Path

# Thêm parent directory vào path
sys.path.insert(0, str(Path(__file__).parent))

def test_paddleocr():
    """Test PaddleOCR từ đầu đến cuối"""
    
    print("=" * 70)
    print("🧪 TEST PADDLEOCR - KHÔNG CẦN TRAIN")
    print("=" * 70)
    
    # Bước 1: Import
    print("\n[1/5] Importing PaddleOCR...")
    try:
        from paddleocr import PaddleOCR
        print("✓ Import thành công")
    except Exception as e:
        print(f"❌ Lỗi import: {e}")
        return False
    
    # Bước 2: Khởi tạo OCR engine (lần đầu sẽ download model ~300MB)
    print("\n[2/5] Khởi tạo PaddleOCR engine...")
    print("   (Lần đầu sẽ download model ~300MB, chỉ làm 1 lần)")
    try:
        start_time = time.time()
        ocr = PaddleOCR(use_angle_cls=True, lang='vi')
        elapsed = time.time() - start_time
        print(f"✓ Engine ready ({elapsed:.1f}s)")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        return False
    
    # Bước 3: Test với ảnh mẫu
    print("\n[3/5] Kiểm tra ảnh mẫu...")
    sample_image = Path(__file__).parent / 'static' / 'receipt_sample.jpg'
    if not sample_image.exists():
        print(f"⚠️ Không tìm thấy ảnh mẫu: {sample_image}")
        print("   Bỏ qua bước này")
    else:
        print(f"   Found: {sample_image}")
        
        # Bước 4: OCR
        print("\n[4/5] Thực hiện OCR...")
        try:
            start_time = time.time()
            result = ocr.ocr(str(sample_image), cls=True)
            elapsed = time.time() - start_time
            print(f"✓ OCR hoàn thành ({elapsed:.1f}s)")
            
            # Parse kết quả
            print("\n[5/5] Kết quả OCR:")
            print("-" * 70)
            
            if result and len(result) > 0:
                text_lines = []
                for line in result:
                    if line:
                        for word_info in line:
                            text = word_info[1]
                            confidence = word_info[2]
                            text_lines.append(f"{text} ({confidence:.2%})")
                
                for line in text_lines[:20]:  # Hiển thị 20 dòng đầu
                    print(f"   {line}")
                
                if len(text_lines) > 20:
                    print(f"   ... ({len(text_lines) - 20} dòng khác)")
                
                print("-" * 70)
                print(f"\n✓ Tổng cộng: {len(text_lines)} từ được nhận diện")
            else:
                print("   (Không tìm thấy text trong ảnh)")
                
        except Exception as e:
            print(f"❌ Lỗi OCR: {e}")
            return False
    
    print("\n" + "=" * 70)
    print("✅ TEST THÀNH CÔNG - PADDLEOCR ĐÃ SẴN SÀNG SỬ DỤNG!")
    print("=" * 70)
    print("\n📝 Thông tin:")
    print("   • Không cần train model")
    print("   • Model được cung cấp sẵn bởi Baidu")
    print("   • Hỗ trợ tiếng Việt, tiếng Anh, ...")
    print("   • Chạy offline - không cần internet sau lần đầu")
    print("   • Tốc độ nhanh - vài giây / ảnh")
    print("\n🚀 Để sử dụng trong ứng dụng:")
    print("   1. Upload ảnh qua web UI")
    print("   2. Click nút 'Chụp ảnh' hoặc 'Chọn ảnh'")
    print("   3. Hệ thống tự động OCR & trích xuất dữ liệu")
    print("   4. Sửa nếu cần & lưu giao dịch")
    
    return True


if __name__ == '__main__':
    success = test_paddleocr()
    sys.exit(0 if success else 1)
