# 🚀 QUICK START - TEST OCR NGAY

## BƯỚC 1: KHỞI CHẠY ỨNG DỤNG

```bash
cd c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech
python app.py
```

Đợi thấy:
```
 * Running on http://127.0.0.1:5000
```

## BƯỚC 2: MỞ TRÌNH DUYỆT

Truy cập: **http://127.0.0.1:5000**

## BƯỚC 3: ĐĂNG NHẬP

**Tài khoản demo:**
- Username: `nguyen_van_a`
- Password: `password123`

Hoặc click nút **"Đăng nhập 1-chạm User"** trên trang login

## BƯỚC 4: VÀO TRANG QUÉT HÓA ĐƠN

1. Click menu **"Ghi chép giao dịch"** (icon plus +)
2. Scroll xuống khu vực **"Quét hóa đơn tự động"**
3. Click để mở rộng

## BƯỚC 5: TEST CAMERA (NẾU CÓ WEBCAM)

1. Click nút **"Chụp ảnh"** (icon camera)
2. Trình duyệt sẽ hỏi quyền camera → Click **"Allow"**
3. Camera sẽ mở trong modal preview
4. Giữ hóa đơn trước camera (rõ nét, không nghiêng)
5. Click **"Chụp ảnh"**
6. Đợi 5-15 giây OCR xử lý

## BƯỚC 6: TEST UPLOAD ẢNH

Nếu không có camera hoặc muốn test với ảnh có sẵn:

1. Click nút **"Chọn ảnh"** (icon image)
2. Chọn ảnh hóa đơn từ máy (JPG/PNG)
3. Đợi 5-15 giây OCR xử lý

**Ảnh test mẫu có sẵn:**
- `static/receipt_sample.jpg` (nếu có)
- Hoặc dùng ảnh hóa đơn thật chụp từ điện thoại

## BƯỚC 7: KIỂM TRA KẾT QUẢ

Sau khi OCR xong, bạn sẽ thấy:

### A. Banner trạng thái:
- ✅ **Xanh:** "Đã quét bằng Tesseract OCR (Offline)" → OCR offline thành công!
- ⚠️ **Vàng:** "Đã quét bằng OCR.space API" → Fallback online (Tesseract chưa cài)
- ❌ **Đỏ:** "Lỗi..." → OCR thất bại

### B. Thông tin nhận diện:
- 🏪 **Tên cửa hàng:** (vd: HIGHLANDS COFFEE)
- 📅 **Ngày giờ:** (vd: 26/11/2026 12:00)
- 💰 **Tổng tiền:** (vd: 125,000đ)
- 📂 **Danh mục:** (vd: Cà phê)

### C. Bảng danh sách món:
| Tên món | SL | Đơn giá | Thành tiền | Danh mục |
|---------|----|---------|-----------:|----------|
| Cà phê đá | 2 | 35,000 | 70,000 | Cà phê |
| Bánh mì | 1 | 25,000 | 25,000 | Ăn uống |
| Nước suối | 2 | 15,000 | 30,000 | Ăn uống |

## BƯỚC 8: CHỈNH SỬA (NẾU CẦN)

OCR không phải 100% chính xác. **Luôn kiểm tra kỹ:**

1. Sửa tên cửa hàng nếu sai
2. Sửa ngày giờ nếu sai
3. Chọn ví thanh toán (Tiền mặt, Thẻ, MoMo, v.v)
4. Sửa tên món/giá trong bảng
5. Thêm món bằng nút **"+ Thêm món"**
6. Xóa món thừa bằng icon thùng rác

## BƯỚC 9: LƯU GIAO DỊCH

1. Kiểm tra tổng tiền cuối cùng
2. Click nút **"Xác nhận & Lưu"** (màu cam)
3. Đợi thông báo "Thành công!"

## BƯỚC 10: KIỂM TRA TRONG LỊCH SỬ

1. Vào trang **"Lịch sử giao dịch"**
2. Xem các giao dịch vừa tạo
3. Mỗi món là 1 transaction
4. Có prefix `[OCR-Tên cửa hàng]` trong description

---

## 🔍 CASE STUDIES - KỲ VỌNG KẾT QUẢ

### Case 1: Hóa đơn siêu thị
**Input:** Ảnh hóa đơn Vinmart  
**Output:**
- ✅ Tên cửa hàng: VINMART (90% đúng)
- ✅ Tổng tiền: 456,000đ (95% đúng)
- ⚠️ Danh sách món: 70% đúng (có thể thiếu/sai một vài món)
- ✅ Danh mục: Mua sắm (90% đúng)

### Case 2: Hóa đơn cà phê
**Input:** Ảnh hóa đơn Highlands  
**Output:**
- ✅ Tên cửa hàng: HIGHLANDS COFFEE (85% đúng)
- ✅ Tổng tiền: 125,000đ (90% đúng)
- ⚠️ Danh sách món: 65% đúng
- ✅ Danh mục: Cà phê (95% đúng)

### Case 3: Hóa đơn xăng dầu
**Input:** Ảnh hóa đơn Petrolimex  
**Output:**
- ✅ Tên cửa hàng: PETROLIMEX (95% đúng)
- ✅ Tổng tiền: 250,000đ (95% đúng)
- N/A Danh sách món (chỉ có 1 món)
- ✅ Danh mục: Đi lại (95% đúng)

---

## ❌ TROUBLESHOOTING

### Lỗi: "Không thể nhận diện hóa đơn"

**Nguyên nhân:**
- Tesseract chưa cài
- OCR.space API hết quota
- Ảnh quá mờ

**Giải pháp:**
1. Cài Tesseract (xem hướng dẫn trên)
2. Thử ảnh rõ hơn
3. Nhập thủ công bằng form bên dưới

### Lỗi: "Không thể mở camera"

**Nguyên nhân:**
- Trình duyệt không hỗ trợ
- Người dùng chặn quyền
- Camera đang được dùng

**Giải pháp:**
1. Dùng Chrome/Edge/Firefox
2. Cấp quyền camera
3. Đóng Zoom/Teams/Skype
4. Fallback: Dùng "Chọn ảnh"

### OCR đọc sai thông tin

**Đây là bình thường!**
- OCR không phải 100% chính xác
- Luôn kiểm tra và sửa trước khi lưu
- Các trường hợp khó: chữ viết tay, ảnh mờ, góc nghiêng

---

## 📊 ĐÁNH GIÁ SAU KHI TEST

Sau khi test, hãy đánh giá:

### Độ chính xác:
- [ ] Tên cửa hàng: đúng / sai / không đọc được
- [ ] Ngày giờ: đúng / sai / không đọc được
- [ ] Tổng tiền: đúng / sai / không đọc được
- [ ] Danh sách món: đầy đủ / thiếu / sai

### Hiệu suất:
- [ ] Thời gian xử lý: <10s / 10-20s / >20s
- [ ] Camera preview: mượt / giật / không hoạt động

### UX:
- [ ] Giao diện: đẹp / tạm ổn / cần cải thiện
- [ ] Dễ sử dụng: có / không
- [ ] Thông báo lỗi: rõ ràng / mơ hồ

---

## 🎯 KẾT LUẬN

**Nếu:**
- ✅ Tesseract đã cài → Banner xanh "Offline"
- ⚠️ Tesseract chưa cài → Banner vàng "OCR.space API"
- ❌ Cả 2 đều lỗi → Thông báo lỗi rõ ràng

**Accuracy kỳ vọng:**
- Tổng tiền: 85-95% ✅
- Tên cửa hàng: 70-90% ✅
- Danh sách món: 60-70% ⚠️

**Luôn cần review trước khi lưu!**

---

**Chúc bạn test thành công! 🎉**
