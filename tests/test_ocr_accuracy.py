#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test độ chính xác OCR hiện tại với ảnh thật
"""
import sys
import os
from pathlib import Path
import io

# Fix encoding cho Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_current_ocr():
    """Test OCR hiện tại"""
    print("=" * 80)
    print("🧪 TEST ĐỘ CHÍNH XÁC OCR HIỆN TẠI")
    print("=" * 80)
    
    # Import module OCR
    print("\n[1] Import OCR module...")
    try:
        from modules.ocr import preprocess_image, scan_with_fallback, TESSERACT_AVAILABLE
        print(f"✓ Import thành công")
        print(f"  - Tesseract available: {TESSERACT_AVAILABLE}")
    except Exception as e:
        print(f"❌ Lỗi import: {e}")
        return
    
    # Kiểm tra ảnh test
    print("\n[2] Tìm ảnh test...")
    image_dir = Path(__file__).parent.parent / 'static' / 'images'
    test_images = list(image_dir.glob('hd*.jpg')) + list(image_dir.glob('hd*.png'))
    
    if not test_images:
        print("❌ Không tìm thấy ảnh test trong static/images/")
        return
    
    print(f"✓ Tìm thấy {len(test_images)} ảnh test")
    for img in test_images:
        print(f"  - {img.name}")
    
    # Test từng ảnh
    print("\n[3] Chạy OCR trên từng ảnh...")
    results = []
    
    for i, img_path in enumerate(test_images[:3], 1):  # Test 3 ảnh đầu tiên
        print(f"\n--- Ảnh {i}/{min(3, len(test_images))}: {img_path.name} ---")
        
        try:
            # Đọc và preprocess ảnh
            with open(img_path, 'rb') as f:
                image_bytes = preprocess_image(f)
            
            print(f"  ✓ Preprocessed: {len(image_bytes)} bytes")
            
            # OCR
            result = scan_with_fallback(image_bytes)
            
            # Hiển thị kết quả
            print(f"\n  📊 Kết quả:")
            print(f"    - Merchant: {result.get('merchant', 'N/A')}")
            print(f"    - Total: {result.get('total_amount', 0):,}đ")
            print(f"    - Date: {result.get('timestamp', 'N/A')}")
            print(f"    - Category: {result.get('category', 'N/A')}")
            print(f"    - Items: {len(result.get('items', []))} món")
            print(f"    - Source: {result.get('source', 'N/A')}")
            print(f"    - Confidence: {result.get('confidence', 0):.0%}")
            
            # Hiển thị items
            items = result.get('items', [])
            if items:
                print(f"\n  🛒 Danh sách món:")
                for j, item in enumerate(items[:5], 1):
                    print(f"    {j}. {item.get('name', 'N/A')} - {item.get('amount', 0):,}đ")
            
            results.append({
                'image': img_path.name,
                'success': True,
                'merchant': result.get('merchant', 'N/A'),
                'total': result.get('total_amount', 0),
                'items_count': len(items),
                'source': result.get('source', 'N/A')
            })
            
        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
            results.append({
                'image': img_path.name,
                'success': False,
                'error': str(e)
            })
    
    # Tổng kết
    print("\n" + "=" * 80)
    print("📈 TỔNG KẾT:")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\nSố ảnh test: {len(results)}")
    print(f"Thành công: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    
    print("\n📋 Chi tiết từng ảnh:")
    for r in results:
        if r.get('success'):
            print(f"\n  ✓ {r['image']}")
            print(f"    Merchant: {r['merchant']}")
            print(f"    Total: {r['total']:,}đ")
            print(f"    Items: {r['items_count']}")
            print(f"    Source: {r['source']}")
        else:
            print(f"\n  ❌ {r['image']}")
            print(f"    Lỗi: {r.get('error', 'Unknown')}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_current_ocr()
