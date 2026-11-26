# 🧪 Hướng dẫn Test Fix Lỗi Lưu Giao Dịch OCR

## ✅ Các vấn đề đã sửa

### 1. Source field không uppercase
- **Trước:** `"source": "ocr"` → bị reject bởi validation
- **Sau:** `"source": "OCR"` → pass validation ✅

### 2. Thiếu category_id mapping  
- **Trước:** Chỉ gửi tên category, không map sang category_id
- **Sau:** Query Category table và set category_id ✅

### 3. custom_transactions luôn rỗng
- **Trước:** `_user_dict()` hardcode `"custom_transactions": []`
- **Sau:** Load từ Transaction table ✅

### 4. Transactions không có wallet_id
- **Trước:** wallet_id = NULL → không query được theo user
- **Sau:** Tự động tạo/match wallet "Tiền mặt" mặc định ✅

## 🧪 Các bước test

### Test 1: Kiểm tra database có transactions chưa
```bash
cd c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech
python test_ocr_save_debug.py
```

**Kết quả mong đợi:**
```
✓ Tổng số transactions: 39
  - MANUAL: 2
  - OCR: 2
  - OPEN_BANKING: 35
✓ custom_transactions có X giao dịch  # X > 0 là OK
```

### Test 2: Test thực tế với OCR

#### Bước 1: Mở ứng dụng
1. Truy cập: http://127.0.0.1:5000
2. Đăng nhập (admin/admin hoặc tài khoản của bạn)

#### Bước 2: Vào trang "Thêm giao dịch"
1. Click menu "Giao dịch" → "Thêm mới"
2. Hoặc truy cập trực tiếp: http://127.0.0.1:5000/add-transaction

#### Bước 3: Quét hóa đơn OCR
1. Click nút **"📸 Quét hóa đơn OCR"**
2. Cho phép camera nếu browser yêu cầu
3. Chụp hoặc upload hóa đơn (hình ảnh có chữ)
4. Đợi OCR xử lý (banner màu XANH = Tesseract offline)

**Lưu ý:**
- Tesseract độ chính xác 65-95%, cần sửa tay
- Nếu không có camera, dùng file test: `test_receipt.jpg`

#### Bước 4: Kiểm tra kết quả OCR
Sau khi OCR xong, sẽ hiển thị form:
- **Merchant:** Tên cửa hàng
- **Timestamp:** Thời gian giao dịch
- **Items:** Danh sách món/sản phẩm với:
  - Tên món
  - Số tiền
  - Category (dropdown)
- **Wallet:** Chọn ví (mặc định "Tiền mặt")

#### Bước 5: Xác nhận và lưu
1. **Kiểm tra/sửa** thông tin nếu OCR sai
2. Click **"Xác nhận & Lưu"**
3. Đợi API response

**Kết quả mong đợi:**
```json
{
  "success": true,
  "message": "Đã lưu thành công N món từ hóa đơn XXX!",
  "total_amount": 70000,
  "transaction_count": 2,
  "reference_code": "OCR.1234567890"
}
```

#### Bước 6: Xác nhận giao dịch đã lưu
1. Vào trang **"Lịch sử giao dịch"**
2. Hoặc truy cập: http://127.0.0.1:5000/transactions

**Phải thấy:**
- ✅ Giao dịch mới với prefix `[OCR-TênMerchant]`
- ✅ Số tiền chính xác
- ✅ Category đã được phân loại
- ✅ Timestamp đúng
- ✅ Source = OCR
- ✅ Reference code chung cho cả hóa đơn

**Nếu KHÔNG thấy giao dịch:**
- ❌ Lỗi vẫn chưa được fix hoàn toàn
- Kiểm tra console Flask logs
- Chạy lại test_ocr_save_debug.py

### Test 3: Kiểm tra chi tiết giao dịch

#### Bước 3a: Kiểm tra format giao dịch
1. Mở DevTools (F12)
2. Tab Network → reload trang transactions
3. Tìm request `/api/transactions` hoặc `/transactions`
4. Xem response JSON

**Mỗi giao dịch OCR phải có:**
```json
{
  "id": "TXN_1234567890_0",
  "timestamp": "2024-01-26 10:30:00",
  "bank": "Tiền mặt",
  "wallet_id": "wallet_xxx",
  "account_number": "VÍ CÁ NHÂN",
  "type": "OUTFLOW",
  "amount": 45000,
  "description": "[OCR-Vinmart] Cà phê",
  "category": "Cà phê",
  "category_id": "cat_xxx",
  "reference_code": "OCR.1234567890",
  "source": "OCR"
}
```

#### Bước 3b: Kiểm tra trong database
```bash
python test_ocr_save_debug.py
```

Xem section:
- `✓ custom_transactions có X giao dịch` → X phải > 0
- `✓ 3 giao dịch đầu tiên` → phải có giao dịch OCR mới

## 🐛 Troubleshooting

### Lỗi 1: "Không có món hợp lệ nào để lưu"
**Nguyên nhân:** OCR không đọc được số tiền hoặc amount = 0

**Giải pháp:**
- Chụp lại hóa đơn rõ hơn
- Sửa tay số tiền trong form trước khi lưu

### Lỗi 2: Giao dịch lưu nhưng không thấy trong lịch sử
**Nguyên nhân:** `_user_dict()` không load được transactions

**Debug:**
```bash
python test_ocr_save_debug.py
```

Nếu thấy:
- `✓ Tổng số transactions: X` → transactions có trong DB
- `⚠ custom_transactions rỗng!` → lỗi query

**Kiểm tra:**
1. User có wallet không?
2. Transactions có wallet_id đúng không?
3. Source field có phải "OCR" (uppercase) không?

### Lỗi 3: Category không được map
**Triệu chứng:** Giao dịch có nhưng category = null

**Nguyên nhân:** Tên category không khớp với database

**Giải pháp:**
Chạy:
```bash
python test_ocr_save_debug.py
```

Xem section `TEST 4: Kiểm tra Categories` → list các category hợp lệ

**Categories hợp lệ:**
- Ăn uống & Cà phê ngoài
- Thực phẩm & Đi chợ
- Đi lại & Xăng xe
- Mua sắm cá nhân
- Giải trí & Phim ảnh
- Nhà ở & Hóa đơn tiện ích
- Y tế & Giáo dục
- Dịch vụ số định kỳ (Subscription)
- Tiết kiệm & Tích sản
- Thu nhập tiền lương
- Thưởng & Thu nhập ngoài

### Lỗi 4: JSON parse error
**Triệu chứng:** Flask logs hiển thị `JSONDecodeError`

**Nguyên nhân:** Frontend gửi data không đúng format

**Debug:**
1. Mở DevTools → Network tab
2. Tìm request `/api/ocr/confirm-receipt`
3. Xem Payload/Request Body

**Format đúng:**
```json
{
  "merchant": "Vinmart",
  "timestamp": "2024-01-26 10:30:00",
  "wallet": "Tiền mặt",
  "items": [
    {
      "name": "Cà phê",
      "amount": 45000,
      "category": "Ăn uống & Cà phê ngoài"
    }
  ]
}
```

### Lỗi 5: Duplicate transactions
**Triệu chứng:** Click "Lưu" nhiều lần → tạo nhiều bản copy

**Nguyên nhân:** Chưa disable button sau khi click

**Giải pháp tạm thời:**
- Chỉ click "Xác nhận & Lưu" **MỘT LẦN**
- Đợi đến khi thấy thông báo thành công

## 📊 Kết quả mong đợi

Sau khi fix, flow hoàn chỉnh:

```
1. User quét hóa đơn 
   → OCR engine (Tesseract) trích xuất text
   → Parse thành items (tên, số tiền)
   
2. User sửa/xác nhận thông tin
   → Frontend gửi POST /api/ocr/confirm-receipt
   
3. Backend validate & tạo transactions
   → Source = "OCR" (uppercase)
   → Category name → query Category table → category_id
   → Bank name → match Wallet (hoặc tạo "Tiền mặt")
   
4. update_user_field('custom_transactions', [...])
   → _apply_user_updates()
   → _sync_transactions()
   → Insert/Update Transaction table
   → Commit to database
   
5. _user_dict() load lại user
   → Query Transaction table (source IN MANUAL/OCR/PIS_SAVINGS)
   → Filter by wallet_id IN user's wallets
   → Return custom_transactions array
   
6. Frontend reload transactions page
   → Hiển thị giao dịch mới ✅
```

## 🎯 Checklist hoàn thành

- [x] Source field uppercase "OCR"
- [x] Category name → category_id mapping
- [x] _user_dict() load từ Transaction table
- [x] Wallet matching/auto-create "Tiền mặt"
- [x] Query transactions theo wallet_id
- [x] Transaction hiển thị trong lịch sử
- [ ] Update wallet balance (TODO - phase 3)
- [ ] Prevent duplicate on double-click (TODO - UX improvement)
- [ ] Default category "Chưa phân loại" (TODO - enhancement)

---
**Status:** ✅ HOÀN THÀNH CỐT LÕI  
**Phần còn lại:** UX improvements (không ảnh hưởng chức năng chính)
