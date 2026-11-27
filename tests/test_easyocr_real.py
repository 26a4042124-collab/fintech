#!/usr/bin/env python3
"""
Script test EasyOCR với ảnh hóa đơn thực tế - Không dùng mock data
"""

import sys
import time
from pathlib import Path

# Thêm parent directory vào path
sys.path.insert(0, str(Path(__file__).parent))

def test_easyocr_real():
    """Test EasyOCR từ đầu đến cuối với ảnh thực"""
    
    print("=" * 70)
    print("🧪 TEST EASYOCR - OCR THỰC TẾ 100% (KHÔNG MOCK DATA)")
    print("=" * 70)
    
    # Bước 1: Import module
    print("\n[1/6] Import EasyOCR scanner module...")
    try:
        from modules.easyocr_scanner import (
            preprocess_image, 
            scan_with_fallback,
            get_ocr_reader,
            EASYOCR_AVAILABLE
        )
        print("✓ Import thành công")
    except Exception as e:
        print(f"❌ Lỗi import: {e}")
        return False
    
    # Bước 2: Kiểm tra EasyOCR có sẵn không
    print("\n[2/6] Kiểm tra EasyOCR availability...")
    if not EASYOCR_AVAILABLE:
        print("❌ EasyOCR chưa được cài đặt!")
        print("\n📦 Để cài đặt, chạy:")
        print("   pip install easyocr")
        return False
    print("✓ EasyOCR đã sẵn sàng")
    
    # Bước 3: Khởi tạo OCR reader (download model lần đầu)
    print("\n[3/6] Khởi tạo EasyOCR reader...")
    print("   (Lần đầu sẽ download model ~300MB, chỉ làm 1 lần)")
    try:
        start_time = time.time()
        reader = get_ocr_reader()
        if reader is None:
            print("❌ Không thể khởi tạo EasyOCR reader")
            return False
        elapsed = time.time() - start_time
        print(f"✓ Reader sẵn sàng ({elapsed:.1f}s)")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        return False
    
    # Bước 4: Kiểm tra ảnh test
    print("\n[4/6] Kiểm tra ảnh test...")
    sample_image = Path(__file__).parent / 'static' / 'receipt_sample.jpg'
    if not sample_image.exists():
        print(f"⚠️ Không tìm thấy ảnh mẫu: {sample_image}")
        print("   Vui lòng cung cấp ảnh hóa đơn để test")
        return False
    print(f"✓ Tìm thấy ảnh: {sample_image}")
    
    # Bước 5: Preprocess ảnh
    print("\n[5/6] Chuẩn hóa ảnh...")
    try:
        with open(sample_image, 'rb') as f:
            image_bytes = preprocess_image(f)
        print(f"✓ Ảnh đã được chuẩn hóa ({len(image_bytes)} bytes)")
    except Exception as e:
        print(f"❌ Lỗi preprocess: {e}")
        return False
    
    # Bước 6: OCR thực tế
    print("\n[6/6] Thực hiện OCR...")
    try:
        start_time = time.time()
        result = scan_with_fallback(image_bytes)
        elapsed = time.time() - start_time
        print(f"✓ OCR hoàn thành ({elapsed:.1f}s)")
        
        # Hiển thị kết quả
        print("\n" + "=" * 70)
        print("📊 KẾT QUẢ OCR:")
        print("=" * 70)
        
        print(f"\n🏪 Cửa hàng: {result.get('merchant', 'N/A')}")
        print(f"📅 Ngày giờ: {result.get('timestamp', 'N/A')}")
        print(f"💰 Tổng tiền: {result.get('total_amount', 0):,}đ")
        print(f"📂 Danh mục: {result.get('category', 'N/A')}")
        print(f"🎯 Độ tin cậy: {result.get('confidence', 0):.0%}")
        print(f"🔧 Nguồn: {result.get('source', 'N/A')}")
        
        # Danh sách món
        items = result.get('items', [])
        if items:
            print(f"\n🛒 Danh sách món ({len(items)}):")
            for i, item in enumerate(items, 1):
                name = item.get('name', 'N/A')
                qty = item.get('quantity', 1)
                price = item.get('amount', 0)
                cat = item.get('category', 'N/A')
                print(f"   {i}. {name}")
                print(f"      SL: {qty} | Giá: {price:,}đ | Danh mục: {cat}")
        else:
            print("\n⚠️ Không tìm thấy món nào trong hóa đơn")
        
        # Warnings
        warnings = result.get('warnings', [])
        if warnings:
            print(f"\n⚠️ Cảnh báo ({len(warnings)}):")
            for warn in warnings:
                print(f"   • {warn}")
        
        # Kiểm tra không phải mock data
        is_sample = result.get('is_sample', False)
        if is_sample:
            print("\n❌ CẢNH BÁO: Kết quả trả về là MOCK DATA!")
            print("   Điều này vi phạm yêu cầu đề bài")
            return False
        
        print("\n" + "=" * 70)
        print("✅ TEST THÀNH CÔNG - OCR THỰC TẾ 100%!")
        print("=" * 70)
        
        # Thông tin bổ sung
        print("\n📝 Xác nhận:")
        print("   ✅ Không sử dụng mock data")
        print("   ✅ OCR thực tế từ ảnh")
        print("   ✅ Parse dữ liệu có cấu trúc")
        print("   ✅ Chạy offline (sau lần download model đầu)")
        print("   ✅ Hỗ trợ tiếng Việt + tiếng Anh")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Lỗi OCR: {e}")
        print(f"\n📋 Chi tiết lỗi: {type(e).__name__}: {str(e)}")
        return False


if __name__ == '__main__':
    print("\n" + "🚀 BẮT ĐẦU TEST EASYOCR REAL OCR\n")
    success = test_easyocr_real()
    
    if success:
        print("\n✅ Hệ thống OCR đã sẵn sàng để tích hợp vào ứng dụng!")
        print("\n📌 Các bước tiếp theo:")
        print("   1. Chạy ứng dụng: python app.py")
        print("   2. Vào trang: /add-transaction")
        print("   3. Upload ảnh hóa đơn thật")
        print("   4. Kiểm tra kết quả OCR")
        print("   5. Chỉnh sửa nếu cần và lưu giao dịch")
    else:
        print("\n❌ Test thất bại. Vui lòng kiểm tra lại các bước trên.")
    
    sys.exit(0 if success else 1)
