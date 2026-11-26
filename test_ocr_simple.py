#!/usr/bin/env python3
"""
Test OCR đơn giản để kiểm tra lỗi
"""

import sys
import os

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("🧪 TEST OCR MODULE")
print("=" * 70)

# Test 1: Import modules
print("\n[1/5] Test import modules...")
try:
    from modules.simple_ocr import (
        preprocess_image,
        scan_with_fallback,
        ReceiptProcessingError,
        TESSERACT_AVAILABLE
    )
    print("✅ Import thành công")
    print(f"   • TESSERACT_AVAILABLE = {TESSERACT_AVAILABLE}")
except Exception as e:
    print(f"❌ Lỗi import: {e}")
    sys.exit(1)

# Test 2: Kiểm tra Pillow
print("\n[2/5] Test Pillow (PIL)...")
try:
    from PIL import Image
    print("✅ Pillow OK")
except Exception as e:
    print(f"❌ Pillow lỗi: {e}")
    sys.exit(1)

# Test 3: Tạo ảnh test đơn giản
print("\n[3/5] Tạo ảnh test đơn giản...")
try:
    from io import BytesIO
    # Tạo ảnh trắng 100x100
    img = Image.new('RGB', (100, 100), color='white')
    
    # Thêm text (nếu có PIL ImageDraw)
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "HIGHLANDS COFFEE", fill='black')
        draw.text((10, 60), "Total: 125,000d", fill='black')
    except:
        pass  # Không có font, bỏ qua
    
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    test_image = img_bytes.getvalue()
    
    print(f"✅ Tạo ảnh test thành công ({len(test_image)} bytes)")
except Exception as e:
    print(f"❌ Lỗi tạo ảnh: {e}")
    sys.exit(1)

# Test 4: Test preprocess
print("\n[4/5] Test preprocess_image...")
try:
    processed = preprocess_image(BytesIO(test_image))
    print(f"✅ Preprocess OK ({len(processed)} bytes)")
except Exception as e:
    print(f"❌ Lỗi preprocess: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test OCR (sẽ thất bại vì ảnh trắng, nhưng kiểm tra flow)
print("\n[5/5] Test OCR engine...")
print("   ⚠️  Sẽ thử OCR với ảnh test (có thể lỗi, OK)")

try:
    result = scan_with_fallback(processed, categories=['Cà phê', 'Ăn uống'])
    print(f"✅ OCR thành công!")
    print(f"   • Source: {result.get('source')}")
    print(f"   • Merchant: {result.get('merchant')}")
    print(f"   • Total: {result.get('total_amount')}")
except RuntimeError as e:
    # Expected error
    print(f"⚠️  OCR thất bại (expected): {str(e)[:100]}...")
    if "Tesseract" in str(e) or "OCR" in str(e):
        print("   → Đây là lỗi bình thường vì:")
        print("      1. Tesseract chưa cài")
        print("      2. OCR.space API có thể không đọc được ảnh trắng")
        print("      3. Ảnh test không có nội dung thực")
except Exception as e:
    print(f"❌ Lỗi không mong đợi: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("📊 KẾT QUẢ:")
print("=" * 70)
print("✅ Import modules: OK")
print("✅ Pillow: OK")
print("✅ Tạo ảnh test: OK")
print("✅ Preprocess: OK")
print("⚠️  OCR: Chưa test với ảnh thật")

print("\n" + "=" * 70)
print("📝 NEXT STEPS:")
print("=" * 70)
print("1. Chạy Flask app: python app.py")
print("2. Mở browser: http://127.0.0.1:5000")
print("3. Đăng nhập: nguyen_van_a / password123")
print("4. Vào 'Ghi chép giao dịch' → 'Quét hóa đơn'")
print("5. Upload ảnh hóa đơn THẬT (chụp từ điện thoại)")
print("6. Nếu lỗi, xem terminal Flask để biết lỗi chi tiết")

print("\n" + "=" * 70)
print("💡 TIPS:")
print("=" * 70)
print("• Nếu banner VÀNG → OCR.space API đang hoạt động (OK)")
print("• Nếu lỗi 'Không đọc được text' → Ảnh quá mờ hoặc API limit")
print("• Để offline: Cài Tesseract (xem CAI_DAT_TESSERACT.md)")
print("=" * 70)
