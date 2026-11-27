# HƯỚNG DẪN TEST CHỨC NĂNG QUÉT HÓA ĐƠN

## ✅ Đã hoàn thành

Chức năng "Quét hóa đơn bằng AI Vision" đã được tích hợp vào app FinLab PFM.

### Các file đã tạo/sửa:

**TẠO MỚI:**
- ✓ `modules/ocr_scanner.py` - Module xử lý OCR với Gemini AI
- ✓ `tests/test_ocr_scanner.py` - 17 unit tests (ALL PASSED)
- ✓ `generate_receipt_sample.py` - Script tạo ảnh mẫu
- ✓ `static/receipt_sample.jpg` - Ảnh hóa đơn mẫu để test

**ĐÃ SỬA:**
- ✓ `app.py` - Thêm 2 routes API: `/api/ocr/scan-receipt`, `/api/ocr/confirm-receipt`
- ✓ `templates/add_transaction.html` - Thêm UI quét hóa đơn đầy đủ
- ✓ `requirements.txt` - Thêm `google-generativeai`, `pytest`
- ✓ `.env.example` + `.env` - Thêm biến `GEMINI_API_KEY`

---

## 🧪 CÁCH TEST

### **1. Chạy Unit Tests (đã test, tất cả PASS)**

```bash
cd "c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech"
python -m pytest tests/test_ocr_scanner.py -v
```

Kết quả: **17 passed** ✓

---

### **2. Test trên giao diện web (3 kịch bản)**

App đang chạy tại: **http://127.0.0.1:5000**

**Đăng nhập:**
- User: `nguyen_van_a` / `password123`
- Hoặc Admin: `admin` / `admin123`

**Vào trang Ghi chép giao dịch:**  
`http://127.0.0.1:5000/add-transaction`

---

### **KỊCH BẢN 1: Test chế độ FALLBACK (không có API key)**

**Hiện tại:** File `.env` để trống `GEMINI_API_KEY=`

**Các bước:**
1. ✅ Mở trang "Ghi chép giao dịch"
2. ✅ Nhấn vào khu "Quét hóa đơn tự động" để mở rộng
3. ✅ Upload ảnh bất kỳ (hoặc dùng `static/receipt_sample.jpg`)
4. ✅ Hệ thống hiển thị **banner đỏ cảnh báo**: 
   > "Không kết nối được dịch vụ AI. Đây là DỮ LIỆU MẪU!"
5. ✅ Kiểm tra dữ liệu mẫu: Quán Cà Phê Mẫu, 3 món, tổng 125.000đ
6. ✅ Sửa thông tin (tên món, số tiền, danh mục) trong bảng
7. ✅ Chọn ví thanh toán
8. ✅ Nhấn "Xác nhận & Lưu"
9. ✅ Kiểm tra giao dịch xuất hiện trong trang "Lịch sử giao dịch"

**Kỳ vọng:** 
- ✅ App vẫn hoạt động bình thường
- ✅ Hiển thị cảnh báo rõ ràng về dữ liệu mẫu
- ✅ Lưu giao dịch thành công (3 transactions với cùng reference_code)

---

### **KỊCH BẢN 2: Test với Gemini AI THẬT**

**Chuẩn bị:**
1. Lấy API key miễn phí tại: https://makersuite.google.com/app/apikey
2. Mở file `.env`, điền vào dòng:
   ```
   GEMINI_API_KEY=YOUR_API_KEY_HERE
   ```
3. Restart app (Ctrl+C trong terminal, sau đó `python app.py`)

**Các bước test:**
1. ✅ Upload ảnh hóa đơn thật (chụp từ điện thoại hoặc tải từ Google Images)
2. ✅ Đợi 3-10 giây (hiện spinner "Đang quét...")
3. ✅ Kiểm tra **banner xanh**: "Đã quét bằng AI Vision"
4. ✅ Xem kết quả: tên cửa hàng, ngày giờ, các món đã nhận diện
5. ✅ Kiểm tra danh mục tự động phân loại cho từng món
6. ✅ Sửa nếu cần (AI có thể nhận diện sai)
7. ✅ Lưu và xác nhận

**Kỳ vọng:**
- ✅ AI đọc được: tên cửa hàng, tổng tiền, danh sách món
- ✅ Tự động phân loại vào đúng rổ chi tiêu (Ăn uống, Cà phê, Di chuyển...)
- ✅ Nếu có lệch tổng tiền → hiển thị warning màu vàng

---

### **KỊCH BẢN 3: Test lỗi và edge cases**

**3.1. Upload file không hợp lệ:**
- ❌ File .txt → "Định dạng ảnh không hợp lệ!"
- ❌ File > 8MB → "File quá lớn! Tối đa 8MB"

**3.2. Ảnh hỏng/mờ:**
- ✅ Upload ảnh mờ hoặc xoay ngược
- ✅ AI vẫn cố đọc, nhưng confidence thấp
- ✅ Hiển thị warning để user kiểm tra lại

**3.3. Không có món nào:**
- ✅ Xóa hết tất cả món trong bảng
- ✅ Nút "Xác nhận & Lưu" bị disable (màu xám)

**3.4. Chọn ảnh khác:**
- ✅ Nhấn "Chọn ảnh khác" → reset về màn hình upload
- ✅ Upload ảnh mới, quét lại từ đầu

**3.5. Hủy giữa chừng:**
- ✅ Nhấn "Hủy" → hỏi xác nhận
- ✅ Confirm → reset toàn bộ

---

## 📊 KẾT QUẢ TRONG DATABASE

Sau khi lưu hóa đơn, kiểm tra file `data/users.json`:

```json
{
  "custom_transactions": [
    {
      "id": "TXN_...",
      "timestamp": "2024-01-15 10:30:00",
      "bank": "Tiền mặt",
      "type": "OUTFLOW",
      "amount": 35000,
      "description": "[OCR-Highlands Coffee] Cà phê: Cà phê đá",
      "reference_code": "OCR.1234567890",
      "source": "ocr"
    },
    {
      "id": "TXN_...",
      "timestamp": "2024-01-15 10:30:00",
      "bank": "Tiền mặt",
      "type": "OUTFLOW",
      "amount": 25000,
      "description": "[OCR-Highlands Coffee] Ăn uống: Bánh mì",
      "reference_code": "OCR.1234567890",
      "source": "ocr"
    }
  ]
}
```

**Đặc điểm:**
- ✅ Mỗi món = 1 transaction riêng
- ✅ Cùng `reference_code` để nhóm lại
- ✅ `source: "ocr"` để phân biệt với nhập thủ công
- ✅ Description có prefix `[OCR-Tên cửa hàng]`

---

## 🔧 TROUBLESHOOTING

### **Lỗi: "Thiếu thư viện google-generativeai"**
```bash
pip install google-generativeai
```

### **Lỗi: "Không tìm thấy module ocr_scanner"**
- Kiểm tra file `modules/ocr_scanner.py` đã tồn tại
- Restart app

### **Warning: "FutureWarning google.generativeai"**
- Không ảnh hưởng chức năng
- Đây là cảnh báo về phiên bản cũ của SDK
- Vẫn hoạt động bình thường

### **API Key không hoạt động:**
1. Kiểm tra key đúng format (bắt đầu bằng `AIza...`)
2. Kiểm tra quota còn miễn phí tại Google AI Studio
3. Kiểm tra mạng có kết nối được đến `generativelanguage.googleapis.com`

### **Quét chậm (> 20 giây):**
- Timeout mặc định 20s
- Nếu timeout → tự động fallback
- Kiểm tra kết nối mạng

---

## 📝 GHI CHÚ KỸ THUẬT

### **Kiến trúc:**
1. **Frontend** (`add_transaction.html`):
   - Khu vực upload drag-drop
   - Preview ảnh + edit fields
   - Bảng items với validation real-time
   - 3 loại banner theo source (gemini/local/fallback)

2. **Backend API** (`app.py`):
   - `POST /api/ocr/scan-receipt`: Upload → Preprocess → Scan → Return JSON
   - `POST /api/ocr/confirm-receipt`: Validate → Create transactions → Save to DB

3. **OCR Engine** (`ocr_scanner.py`):
   - Preprocess: Resize, rotate EXIF, enhance contrast
   - Gemini Vision: JSON schema strict, prompt tiếng Việt
   - Normalize: Parse amount VN format, validate timestamp
   - Fallback: Sample data với warning rõ ràng

### **Bảo mật:**
- ✅ API key từ env, không commit vào git
- ✅ File validation: type, size, format
- ✅ Server-side validation: category, amount, wallet
- ✅ CSRF token (nếu có trong form)
- ✅ Escape HTML trong table để tránh XSS

### **Hiệu năng:**
- ✅ Resize ảnh xuống max 1600px trước khi gửi API
- ✅ JPEG quality 85 để giảm dung lượng
- ✅ Timeout 20s cho mỗi request
- ✅ Không lưu file tạm, xử lý trong memory

---

## 🎯 ĐÁNH GIÁ CHỨC NĂNG

| Yêu cầu | Trạng thái | Ghi chú |
|---------|-----------|---------|
| Chuẩn hóa ảnh (xoay, resize, enhance) | ✅ | Dùng Pillow |
| Quét bằng Gemini Vision API | ✅ | JSON schema strict |
| Fallback offline khi không có mạng | ✅ | Dữ liệu mẫu với warning |
| UI upload drag-drop | ✅ | Responsive |
| Bảng kiểm tra từng món | ✅ | Edit inline |
| Tự động phân loại danh mục | ✅ | Theo categories có sẵn |
| Lưu nhiều giao dịch (1 món = 1 txn) | ✅ | Group bằng reference_code |
| Không làm hỏng chức năng cũ | ✅ | Form thủ công vẫn hoạt động |
| Test coverage | ✅ | 17/17 tests PASS |
| Bảo mật API key | ✅ | Từ .env, không log |

---

## 📚 TÀI LIỆU THAM KHẢO

- Gemini API Documentation: https://ai.google.dev/docs
- Lấy API key miễn phí: https://makersuite.google.com/app/apikey
- Pillow docs: https://pillow.readthedocs.io/
- Flask file upload: https://flask.palletsprojects.com/en/2.3.x/patterns/fileuploads/

---

## ✨ ĐIỂM NỔI BẬT

1. **Hoạt động offline:** Không có API key vẫn dùng được (fallback mode)
2. **UX thân thiện:** Banner màu rõ ràng theo từng trường hợp
3. **Độ chính xác cao:** Gemini 1.5 Flash nhận diện tốt hóa đơn VN
4. **Dễ mở rộng:** Có thể thêm Tesseract OCR local làm fallback thứ 2
5. **Test đầy đủ:** 17 unit tests cover các edge cases

---

**Chúc bạn test thành công! 🎉**

Nếu gặp vấn đề, kiểm tra log trong terminal Flask hoặc console trình duyệt (F12).
