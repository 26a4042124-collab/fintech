# 🔧 HƯỚNG DẪN CÀI TESSERACT OCR - OCR THẬT 100%

## ⚡ CÁCH NHANH NHẤT (3 PHÚT)

### Bước 1: Tải Tesseract
File đã được tải sẵn tại:
```
C:\Users\nguye\AppData\Local\Temp\tesseract-setup.exe
```

### Bước 2: Cài đặt
1. **Mở File Explorer** (Win + E)
2. **Paste vào thanh địa chỉ:**
   ```
   %TEMP%
   ```
3. **Tìm file:** `tesseract-setup.exe`
4. **Click đúp** để cài đặt
5. **Next → Next → Install**
6. **Quan trọng:** Tick vào **"Vietnamese"** trong danh sách ngôn ngữ!

### Bước 3: Test
Sau khi cài xong, chạy lệnh này:
```bash
tesseract --version
```

Nếu thấy version → **Cài thành công!**

---

## 🚀 SAU KHI CÀI XONG

### Restart app Flask:
Trong terminal đang chạy app, nhấn:
- **Ctrl + C** (dừng)
- Chạy lại: `python app.py`

### Test OCR:
1. Vào http://127.0.0.1:5000/add-transaction
2. Upload ảnh hóa đơn
3. Lần này sẽ thấy **text thật** được đọc từ ảnh!

---

## ❓ NẾU GẶP LỖI "Tesseract not found"

### Fix 1: Thêm vào PATH
1. **Mở System Environment Variables**
2. **Path** → **Edit** → **New**
3. Thêm:
   ```
   C:\Program Files\Tesseract-OCR
   ```
4. **OK** → **Restart terminal**

### Fix 2: Hoặc set trong code (đã làm sẵn)
App tự động tìm Tesseract tại các vị trí phổ biến.

---

## 🎯 KẾT QUẢ KỲ VỌNG

Sau khi cài Tesseract + restart app:

✅ Upload ảnh hóa đơn  
✅ OCR đọc **text thật** từ ảnh (3-5 giây)  
✅ Tự động parse: tên cửa hàng, số tiền, danh sách món  
✅ Hiển thị trong bảng để sửa  
✅ Lưu vào database  

**Banner sẽ hiển thị:** "Đã quét bằng Tesseract OCR"

---

## 💡 TẠI SAO TESSERACT?

- ✅ **Chạy offline** - không cần internet
- ✅ **Miễn phí** - open source
- ✅ **Hỗ trợ tiếng Việt** - đọc hóa đơn VN tốt
- ✅ **Nhanh** - 3-5 giây/ảnh
- ✅ **Không cần train** - model có sẵn

---

**Cài xong báo tôi để restart app nhé!** 🚀
