# 🔧 Khắc phục lỗi lưu giao dịch OCR

## Vấn đề đã phát hiện

Khi người dùng quét hóa đơn bằng OCR và nhấn "Xác nhận & Lưu", giao dịch **không được lưu vào cơ sở dữ liệu** mặc dù API trả về thông báo thành công.

## Nguyên nhân

### 1. Source field không đúng format
- **Trước:** `source: "ocr"` (chữ thường)
- **Sau:** `source: "OCR"` (chữ hoa)
- Hàm `_sync_transactions()` trong `modules/auth.py` line 445 kiểm tra uppercase: `("OPEN_BANKING", "MANUAL", "OCR", "PIS_SAVINGS")`

### 2. Thiếu category_id mapping
- OCR endpoint gửi field `category` (tên danh mục) nhưng không map sang `category_id`
- Hàm `_sync_transactions()` **không có logic** để tra cứu Category ID từ tên danh mục
- Result: Giao dịch được lưu nhưng không có category, description thiếu thông tin

## Giải pháp đã áp dụng

### File: `app.py` (line ~1662)
**Thay đổi 1:** Uppercase source field
```python
# TRƯỚC
"source": "ocr"

# SAU  
"source": "OCR"
```

**Thay đổi 2:** Tách category ra field riêng và đơn giản hóa description
```python
# TRƯỚC
"description": f"[OCR-{merchant}] {item['category']}: {item['name']}",
"source": "ocr"

# SAU
"description": f"[OCR-{merchant}] {item['name']}",
"category": item['category'],
"source": "OCR"
```

### File: `modules/auth.py` (line 422-433)
**Thêm logic:** Map category name → category_id
```python
def _sync_transactions(db, row, items):
    from modules.database import Transaction, Category  # ✅ Thêm Category import
    
    # ... existing code ...
    
    # ✅ THÊM MỚI: Map category name to category_id
    category_name = item.get("category")
    if category_name:
        category = db.query(Category).filter(Category.category_name == str(category_name)).first()
        if category:
            txn.category_id = category.id
```

## Kiểm tra lại

### Trước khi fix
1. Quét hóa đơn OCR → hiển thị kết quả
2. Nhấn "Xác nhận & Lưu" → API trả về success
3. Vào trang Giao dịch → **KHÔNG có giao dịch mới** ❌

### Sau khi fix
1. Quét hóa đơn OCR → hiển thị kết quả
2. Nhấn "Xác nhận & Lưu" → API trả về success
3. Vào trang Giao dịch → **Thấy giao dịch mới với đầy đủ thông tin** ✅
   - Timestamp đúng
   - Số tiền đúng
   - Category được phân loại
   - Description có prefix [OCR-TênMerchant]
   - Source = OCR
   - Reference code chung cho cả hóa đơn

## Technical Details

### Database Schema
```
Transaction table có các field:
- id (primary key)
- wallet_id (foreign key → Wallet)
- category_id (foreign key → Category)  ⚠️ Đây là field bị thiếu
- timestamp
- type (INFLOW/OUTFLOW)
- amount
- description
- source (MANUAL/OCR/OPEN_BANKING/PIS_SAVINGS)
- reference_code
- receipt_meta_json
```

### Flow lưu giao dịch OCR
1. Frontend gửi POST `/api/ocr/confirm-receipt` với:
   ```json
   {
     "merchant": "Vinmart",
     "timestamp": "2024-01-15 10:30:00",
     "wallet": "Tiền mặt",
     "items": [
       {"name": "Cà phê", "amount": 45000, "category": "Cà phê"},
       {"name": "Bánh mì", "amount": 25000, "category": "Ăn uống"}
     ]
   }
   ```

2. Backend (`app.py` line 1577):
   - Validate dữ liệu
   - Tạo array `new_transactions` với format:
     ```python
     {
       "id": "TXN_1234567890_0",
       "timestamp": "2024-01-15 10:30:00",
       "bank": "Tiền mặt",
       "type": "OUTFLOW",
       "amount": 45000,
       "description": "[OCR-Vinmart] Cà phê",
       "category": "Cà phé",  # ✅ Field mới thêm
       "reference_code": "OCR.1234567890",
       "source": "OCR"  # ✅ Uppercase
     }
     ```

3. Call `update_user_field(user_id, 'custom_transactions', transactions)`

4. Auth module (`modules/auth.py`):
   - `update_user_field()` → `update_user()` → `_apply_user_updates()`
   - `_apply_user_updates()` line 497 detect `custom_transactions` field
   - Call `_sync_transactions(db, user_row, transactions)`

5. `_sync_transactions()` function (line 422):
   - Loop qua từng transaction
   - Match wallet theo tên (casefold)
   - **[MỚI]** Query Category theo tên → lấy category_id
   - Insert/Update vào Transaction table
   - Commit to database

## Impact
- **Chi phí:** Minimal - chỉ thêm 1 query Category lookup mỗi transaction
- **Performance:** Không ảnh hưởng - Category table nhỏ, có index
- **Backward compatibility:** ✅ Không ảnh hưởng giao dịch cũ
- **User experience:** ✅✅✅ Giao dịch OCR giờ được lưu đầy đủ thông tin

## Các vấn đề còn lại (KHÔNG khắc phục trong lần này)
1. ⚠️ OCR accuracy 65-95% - đây là giới hạn của Tesseract, cần user sửa tay
2. ⚠️ Chưa có wallet balance update - cần implement riêng
3. ⚠️ Category mapping nếu tên không khớp → giao dịch không có category
4. ⚠️ Duplicate transaction nếu user click "Lưu" nhiều lần

## Khuyến nghị tiếp theo
1. Thêm loading spinner khi click "Xác nhận & Lưu"
2. Disable button sau khi click để tránh duplicate
3. Add toast notification sau khi lưu thành công
4. Redirect về trang Giao dịch sau khi lưu
5. Cân nhắc tạo default Category "Chưa phân loại" cho items không match

---
**Người fix:** AI Assistant  
**Ngày:** 2024-01-26  
**Version:** FinTech Phase 2 OCR Module  
**Status:** ✅ HOÀN THÀNH
