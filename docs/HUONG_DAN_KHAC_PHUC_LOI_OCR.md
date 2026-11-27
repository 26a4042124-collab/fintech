# 🔧 HƯỚNG DẪN KHẮC PHỤC LỖI OCR

## 📊 TÌNH TRẠNG HIỆN TẠI

✅ **Module OCR đã hoạt động:**
- Import modules: OK
- Pillow: OK
- Preprocess: OK
- OCR engine: OK (nhưng thiếu Tesseract)

⚠️ **Vấn đề:**
- Tesseract chưa cài → Không có OCR offline
- OCR.space API hoạt động → Nhưng có thể bị rate limit
- Khi import hóa đơn bị lỗi → Do ảnh không đủ rõ hoặc API limit

---

## 🚀 GIẢI PHÁP 1: TEST VỚI ẢNH HÓA ĐƠN THẬT (NGAY LẬP TỨC)

### Bước 1: Chuẩn bị ảnh hóa đơn

**Yêu cầu ảnh:**
- ✅ **Chụp rõ nét** - Chữ đọc được bằng mắt
- ✅ **Ánh sáng tốt** - Không tối, không chói
- ✅ **Góc vuông** - Không nghiêng quá 15 độ
- ✅ **Toàn bộ hóa đơn** - Không bị cắt
- ✅ **Format:** JPG, PNG
- ✅ **Kích thước:** < 8MB

**Nguồn ảnh:**
1. Chụp hóa đơn thật từ điện thoại
2. Tìm ảnh hóa đơn mẫu trên Google Images
3. Dùng ảnh có sẵn trong máy

### Bước 2: Khởi động Flask app

```bash
# Mở terminal mới
cd c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech
python app.py

# Để terminal mở, không đóng
# Xem log lỗi nếu có
```

### Bước 3: Test trên web

1. Mở browser: **http://127.0.0.1:5000**
2. Đăng nhập: `nguyen_van_a` / `password123`
3. Click **"Ghi chép giao dịch"** (menu trái)
4. Scroll xuống **"Quét hóa đơn tự động"**
5. Click để mở rộng
6. Click **"Chọn ảnh"**
7. Chọn ảnh hóa đơn THẬT từ máy
8. Đợi 5-15 giây

### Bước 4: Kiểm tra kết quả

**Nếu thành công:**
- ✅ Banner **VÀNG** hiện "OCR.space API"
- ✅ Thông tin được fill: tên cửa hàng, tổng tiền, danh sách món
- ✅ Có thể sai một vài chỗ → Sửa lại và lưu

**Nếu lỗi:**
- ❌ Xem thông báo lỗi trên web
- ❌ Xem log trong terminal Flask
- ❌ Đọc tiếp phần Troubleshooting bên dưới

---

## 🔧 GIẢI PHÁP 2: CÀI TESSERACT ĐỂ OCR OFFLINE (5 PHÚT)

### Tại sao cần Tesseract?

| Với OCR.space API | Với Tesseract |
|-------------------|---------------|
| ⚠️ Cần internet | ✅ Offline 100% |
| ⚠️ Có rate limit | ✅ Không giới hạn |
| ⚠️ Chậm (5-10s) | ✅ Nhanh (3-5s) |
| ⚠️ Banner VÀNG | ✅ Banner XANH |

### Cài Tesseract:

**Bước 1: Download**
```
Link: https://github.com/UB-Mannheim/tesseract/wiki
File: tesseract-ocr-w64-setup-v5.3.3.20231005.exe
```

**Bước 2: Cài đặt**
1. Chạy file `.exe`
2. Click Next → Next
3. **QUAN TRỌNG:** Tick ✅ **"Vietnamese language data"**
4. Click Install
5. Đợi 1-2 phút
6. Click Finish

**Bước 3: Kiểm tra**
```bash
# Mở terminal mới
tesseract --version
# Phải thấy: tesseract 5.x.x

tesseract --list-langs
# Phải thấy: eng, vie
```

**Bước 4: Restart Flask app**
```bash
# Trong terminal đang chạy Flask
# Nhấn Ctrl+C để dừng
# Chạy lại:
python app.py
```

**Bước 5: Test lại**
- Upload ảnh hóa đơn
- Lần này banner sẽ **XANH** "Tesseract OCR (Offline)"
- Xử lý nhanh hơn, không cần internet

---

## ❓ TROUBLESHOOTING - CÁC LỖI THƯỜNG GẶP

### Lỗi 1: "Không đọc được text từ ảnh"

**Nguyên nhân:**
- Ảnh quá mờ
- Ảnh bị nghiêng
- OCR.space API hết quota
- Tesseract chưa cài

**Giải pháp:**
1. **Thử ảnh khác rõ hơn**
2. **Cài Tesseract** (xem trên)
3. **Chờ 1 giờ** nếu API hết quota
4. **Nhập thủ công** bằng form bên dưới

---

### Lỗi 2: "File quá lớn! Tối đa 8MB"

**Giải pháp:**
- Nén ảnh xuống < 8MB
- Dùng tool online: https://tinypng.com
- Hoặc resize trong Paint: Save as JPEG, quality 80%

---

### Lỗi 3: "Định dạng ảnh không hợp lệ"

**Giải pháp:**
- Chỉ dùng: JPG, PNG, WEBP
- Không dùng: PDF, GIF, BMP
- Convert bằng Paint: Open → Save As → JPEG

---

### Lỗi 4: Banner ĐỎNG "Lỗi xử lý hóa đơn"

**Giải pháp:**
1. Xem log trong terminal Flask
2. Chụp màn hình log gửi để debug
3. Thử ảnh khác
4. Restart Flask app

---

### Lỗi 5: OCR đọc sai thông tin

**Đây KHÔNG phải lỗi!**
- OCR không 100% chính xác
- Độ chính xác: 70-95% tùy loại hóa đơn
- **Luôn kiểm tra và sửa trước khi lưu**

**Các lỗi thường gặp:**
- Nhầm số 0 với chữ O
- Nhầm số 1 với chữ I
- Đọc thiếu món
- Đọc sai giá tiền

**Giải pháp:**
- Sửa trong bảng edit
- Thêm món bằng "+" nếu thiếu
- Xóa món thừa bằng icon thùng rác

---

### Lỗi 6: "Không thể mở camera"

**Nguyên nhân:**
- Trình duyệt không hỗ trợ
- Người dùng chặn quyền
- Camera đang được dùng (Zoom, Teams)

**Giải pháp:**
1. Dùng Chrome/Edge (không dùng IE)
2. Cấp quyền camera khi hỏi
3. Đóng Zoom, Teams, Skype
4. **Fallback:** Dùng "Chọn ảnh" thay vì camera

---

## 📝 CHECKLIST DEBUG

Nếu vẫn lỗi, check từng bước:

```
□ Flask app đang chạy? (xem terminal)
□ Browser mở được http://127.0.0.1:5000 ?
□ Đăng nhập thành công?
□ Vào được trang "Ghi chép giao dịch"?
□ Thấy khu vực "Quét hóa đơn tự động"?
□ Click mở rộng được?
□ Upload ảnh thành công? (không lỗi ngay)
□ Thấy spinner "Đang quét..."?
□ Sau 5-15 giây có kết quả hoặc lỗi?
```

Nếu застопор ở bước nào, chụp màn hình gửi để debug.

---

## 🎯 KẾT LUẬN

**Hiện tại bạn CÓ THỂ:**
✅ Upload ảnh hóa đơn thật
✅ OCR.space API sẽ xử lý (cần internet)
✅ Banner VÀNG là bình thường
✅ Sửa thông tin nếu OCR sai
✅ Lưu giao dịch

**Để tốt hơn:**
🔧 Cài Tesseract → OCR offline
🔧 Banner XANH
🔧 Nhanh hơn, không cần internet

---

## 📞 NẾU VẪN GẶP VẤN ĐỀ

**Cung cấp thông tin sau:**
1. Screenshot trang web khi lỗi
2. Log trong terminal Flask (copy text)
3. Mô tả: Làm gì → Lỗi gì
4. Ảnh hóa đơn đang test (nếu có thể)

**Các lỗi đã biết:**
- OCR.space API đôi khi bị rate limit → Chờ 1 giờ hoặc cài Tesseract
- Ảnh quá mờ → OCR không đọc được → Thử ảnh khác
- Ảnh không có chữ → OCR trả rỗng → Thử ảnh hóa đơn thật

---

**🎉 Chúc bạn thành công!**
