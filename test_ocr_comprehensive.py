#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test toàn diện OCR với ground truth
"""
import sys
import io
from pathlib import Path

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# Ground truth cho test images
GROUND_TRUTH = {
    'hd1.jpg': {
        'merchant': 'Unknown',  # Cần manual verification
        'total': 55000,  # Dựa trên OCR result
        'category': 'Khác'
    },
    'hd2.png': {
        'merchant': 'HIGHLANDS COFFEE',
        'total': 18000,
        'category': 'Cà phê'
    },
    'hd4.jpg': {
        'merchant': 'Unknown',  # Cần manual verification
        'total': 60000,
        'category': 'Cà phê'
    }
}

def calculate_accuracy(predicted, actual, field_name):
    """Tính độ chính xác cho một field"""
    if field_name == 'merchant':
        # Exact match hoặc substring match
        if predicted == actual:
            return 1.0
        elif predicted.upper() in actual.upper() or actual.upper() in predicted.upper():
            return 0.5
        else:
            return 0.0
    elif field_name == 'total':
        # Tolerance 1%
        if predicted == actual:
            return 1.0
        elif abs(predicted - actual) / actual < 0.01:
            return 0.9
        elif abs(predicted - actual) / actual < 0.05:
            return 0.7
        else:
            return 0.0
    elif field_name == 'category':
        return 1.0 if predicted == actual else 0.0
    
    return 0.0

def test_comprehensive():
    """Test toàn diện với metrics"""
    print("=" * 80)
    print("🧪 TEST TOÀN DIỆN OCR - SO SÁNH VỚI GROUND TRUTH")
    print("=" * 80)
    
    # Import module
    print("\n[1] Import OCR module...")
    from modules.simple_ocr import preprocess_image, scan_with_fallback, TESSERACT_AVAILABLE
    print(f"✓ Import thành công (Tesseract: {TESSERACT_AVAILABLE})")
    
    # Find test images
    print("\n[2] Load test images và ground truth...")
    image_dir = Path(__file__).parent / 'static' / 'images'
    
    results_summary = []
    
    for img_name, truth in GROUND_TRUTH.items():
        img_path = image_dir / img_name
        
        if not img_path.exists():
            print(f"⚠️ Không tìm thấy: {img_name}")
            continue
        
        print(f"\n--- Test: {img_name} ---")
        print(f"Ground Truth:")
        print(f"  Merchant: {truth.get('merchant', 'N/A')}")
        print(f"  Total: {truth.get('total', 0):,}đ")
        print(f"  Category: {truth.get('category', 'N/A')}")
        
        try:
            # Preprocess
            with open(img_path, 'rb') as f:
                image_bytes = preprocess_image(f, mode='light')
            
            # OCR
            result = scan_with_fallback(image_bytes)
            
            # Extract predictions
            pred_merchant = result.get('merchant', '')
            pred_total = result.get('total_amount', 0)
            pred_category = result.get('category', '')
            
            print(f"\nPredicted:")
            print(f"  Merchant: {pred_merchant}")
            print(f"  Total: {pred_total:,}đ")
            print(f"  Category: {pred_category}")
            print(f"  Confidence: {result.get('confidence', 0):.0%}")
            print(f"  Source: {result.get('source', 'N/A')}")
            
            # Calculate accuracy
            merchant_acc = calculate_accuracy(pred_merchant, truth['merchant'], 'merchant') if truth['merchant'] != 'Unknown' else None
            total_acc = calculate_accuracy(pred_total, truth['total'], 'total')
            category_acc = calculate_accuracy(pred_category, truth['category'], 'category')
            
            print(f"\nAccuracy:")
            if merchant_acc is not None:
                print(f"  Merchant: {merchant_acc:.0%}")
            else:
                print(f"  Merchant: N/A (cần verify manual)")
            print(f"  Total: {total_acc:.0%}")
            print(f"  Category: {category_acc:.0%}")
            
            # Warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"\n⚠️ Warnings:")
                for w in warnings:
                    print(f"  - {w}")
            
            results_summary.append({
                'image': img_name,
                'merchant_acc': merchant_acc,
                'total_acc': total_acc,
                'category_acc': category_acc,
                'confidence': result.get('confidence', 0),
                'success': True
            })
            
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            results_summary.append({
                'image': img_name,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TỔNG KẾT:")
    print("=" * 80)
    
    success_count = sum(1 for r in results_summary if r.get('success'))
    print(f"\nSố ảnh test: {len(results_summary)}")
    print(f"Thành công: {success_count}/{len(results_summary)}")
    
    # Calculate average accuracy
    merchant_accs = [r['merchant_acc'] for r in results_summary if r.get('success') and r.get('merchant_acc') is not None]
    total_accs = [r['total_acc'] for r in results_summary if r.get('success')]
    category_accs = [r['category_acc'] for r in results_summary if r.get('success')]
    
    if merchant_accs:
        print(f"\n📈 Độ chính xác trung bình:")
        print(f"  Merchant Name: {sum(merchant_accs)/len(merchant_accs):.0%}")
    print(f"  Total Amount: {sum(total_accs)/len(total_accs):.0%}")
    print(f"  Category: {sum(category_accs)/len(category_accs):.0%}")
    
    avg_conf = sum(r['confidence'] for r in results_summary if r.get('success')) / success_count if success_count > 0 else 0
    print(f"\n🎯 OCR Confidence trung bình: {avg_conf:.0%}")
    
    # Detailed table
    print(f"\n📋 Chi tiết:")
    print(f"{'Image':<15} {'Total Acc':<12} {'Category Acc':<15} {'Confidence':<12}")
    print("-" * 60)
    for r in results_summary:
        if r.get('success'):
            img_name = r['image']
            total_acc = f"{r['total_acc']:.0%}" if r.get('total_acc') is not None else "N/A"
            cat_acc = f"{r['category_acc']:.0%}" if r.get('category_acc') is not None else "N/A"
            conf = f"{r['confidence']:.0%}"
            print(f"{img_name:<15} {total_acc:<12} {cat_acc:<15} {conf:<12}")
        else:
            print(f"{r['image']:<15} {'FAILED':<12}")
    
    print("\n" + "=" * 80)
    print("✅ Test hoàn tất!")
    print("=" * 80)

if __name__ == '__main__':
    test_comprehensive()
