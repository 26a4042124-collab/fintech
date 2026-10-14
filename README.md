# 🏦 FinLab - Trợ lý Quản lý Tài chính Cá nhân & Cảnh báo Rò rỉ Chi tiêu Thông minh
> **Dự án Bài tập lớn cuối kỳ môn học: Công nghệ dịch vụ tài chính (FinTech)**  
> **Khoa Công nghệ Thông tin & Kinh tế số - Học viện Ngân hàng (HVNH)**

---

## 🌟 Giới thiệu Dự án
**FinLab** là nền tảng quản lý tài chính cá nhân thế hệ mới, giải quyết triệt để 2 "bẫy tài chính" phổ biến của người trẻ:
1. **Rò rỉ dịch vụ số (Subscription Leaks):** Các khoản đăng ký định kỳ trừ ngầm tự động (Netflix, Spotify, iCloud...).
2. **Chi tiêu bốc đồng ban đêm (Night Impulse Spending):** Các đơn hàng mua sắm Shopee, TikTok Shop, GrabFood phát sinh sau 22h00 đêm khi tâm lý cảm xúc lấn át lý trí.

Ứng dụng kết hợp 2 công nghệ tài chính cốt lõi:
- **Open Banking API (AIS):** Giả lập kết nối chuẩn *Thông tư 64/2024/TT-NHNN* tổng hợp dữ liệu giao dịch từ 3 ngân hàng lớn (Vietcombank, Techcombank, MB Bank) qua cơ chế OAuth 2.0 Consent.
- **Trí tuệ nhân tạo (AI & NLP):** Tự động phân loại giao dịch theo quy tắc chuẩn **50/30/20** (Thiết yếu 50% - Mong muốn 30% - Tiết kiệm 20%), chấm Điểm sức khỏe tài chính (0-100) và tích hợp **Trợ lý ảo AI Chatbot** trò chuyện, tư vấn tài chính theo thời gian thực.

---

## 📂 Cấu trúc Thư mục Dự án

```text
fintech/
├── app.py                      # File khởi chạy chính của ứng dụng Flask
├── requirements.txt            # Danh sách thư viện Python cần thiết
├── README.md                   # Hướng dẫn chi tiết sử dụng & thuyết trình
│
├── data/                       # Dữ liệu mẫu (Database giả lập)
│   ├── users.json              # Tài khoản đăng nhập demo
│   └── mock_transactions.json  # 35 giao dịch thực tế từ VCB, TCB, MB
│
├── modules/                    # Các module xử lý nghiệp vụ backend
│   ├── auth.py                 # Xác thực tài khoản & phiên đăng nhập
│   ├── open_banking.py         # Giả lập kết nối Open Banking API & Consent
│   ├── ai_categorizer.py       # AI NLP phân loại giao dịch & gắn nhãn 50/30/20
│   ├── health_scoring.py       # Thuật toán tính Điểm sức khỏe & kiểm toán rò rỉ
│   └── chatbot_ai.py           # Logic Trợ lý ảo AI Chatbot tư vấn tài chính
│
├── static/                     # Tài nguyên giao diện tĩnh
│   ├── css/
│   │   └── style.css           # Giao diện FinTech chuẩn hiện đại, responsive
│   └── js/
│       ├── main.js             # Điều khiển biểu đồ Chart.js, bộ lọc & Open API modal
│       └── chatbot.js          # Widget Trợ lý AI Chatbot góc dưới bên phải
│
└── templates/                  # Giao diện HTML (Jinja2 Template)
    ├── login.html              # Màn hình đăng nhập (có nút 1-chạm Demo)
    └── dashboard.html          # Bảng điều khiển tài chính trung tâm
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy (Chỉ 2 bước)

### Bước 1: Mở Terminal / PowerShell và di chuyển vào thư mục dự án
```bash
cd F:\amazing-noether\fintech
```

*(Nếu chưa cài thư viện Flask và Pandas)*:
```bash
pip install -r requirements.txt
```

### Bước 2: Chạy ứng dụng Flask
```bash
python app.py
```

Sau đó, mở trình duyệt web và truy cập địa chỉ:  
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Tài khoản Đăng nhập Demo Thuyết trình

Trên màn hình đăng nhập, bạn có thể:
- Bấm trực tiếp nút: **"⚡ Đăng nhập nhanh: Nguyễn Văn A (Demo 1 chạm)"** để vào thẳng Dashboard.
- Hoặc điền thủ công:
  - **Tên đăng nhập:** `nguyen_van_a`
  - **Mật khẩu:** `password123`

---

## 💡 Kịch bản Demo Ấn tượng khi Thuyết trình (Live Demo Walkthrough)

1. **Bước 1 (Đăng nhập):** Giới thiệu trang đăng nhập chuyên nghiệp, bấm nút *Đăng nhập nhanh 1-chạm*.
2. **Bước 2 (Tổng quan Dashboard):**
   - Chỉ vào 4 thẻ chỉ số: Thu nhập 18.000.000đ, Chi tiêu 17.100.000đ (95% - vượt mức), Quỹ tiết kiệm chỉ còn 900.000đ (5% thay vì 20%).
   - Giải thích **Điểm sức khỏe tài chính: 62/100 (Mức Cảnh báo)** do quỹ tiết kiệm quá mỏng và nhóm Mong muốn vượt chuẩn.
3. **Bước 3 (2 Bẫy rò rỉ dòng tiền):**
   - Rò rỉ Subscriptions: 3 gói dịch vụ trừ thẻ ngầm (Netflix, Spotify, iCloud).
   - Rò rỉ Mua sắm đêm: 8 đơn hàng Shopee/TikTok/Ăn khuya sau 22h00 đêm tổng cộng hơn 2.7 triệu đồng.
4. **Bước 4 (Biểu đồ 50/30/20 & Phác đồ hành động AI):**
   - Biểu đồ tròn trực quan hóa sự chênh lệch so với chuẩn 50/30/20.
   - Danh sách các khuyến nghị cụ thể bằng con số từ AI để bù đắp 2.7 triệu thiếu hụt.
5. **Bước 5 (Đồng bộ Open Banking API):**
   - Bấm nút **"Open Banking API"** trên thanh Navbar để mở Modal cấp quyền OAuth 2.0.
   - Bấm **"Kết nối & Đồng bộ ngay"** để mô phỏng tiến trình tải dữ liệu thời gian thực.
6. **Bước 6 (Tương tác Trợ lý ảo AI Chatbot):**
   - Bấm vào biểu tượng Chatbot hình tròn ở góc phải bên dưới (hoặc icon Trợ lý AI ở thanh điều hướng đáy trên Mobile).
   - Bấm các câu hỏi gợi ý nhanh:
     - *"Chi tiêu ăn uống tháng này?"*
     - *"Có khoản đăng ký ngầm nào đang trừ tiền không?"*
     - *"Tại sao điểm sức khỏe tài chính của tôi lại thấp?"*
     - *"Làm sao để tôi tiết kiệm thêm 2.7 triệu mỗi tháng?"*
   - Chatbot sẽ phản hồi tức thì với dữ liệu phân tích chuẩn xác!
7. **Bước 7 (Trình diễn Giao diện Mobile App):**
   - Bấm nút **"📱 Chế độ App"** ngay trên thanh Navbar: Màn hình lập tức chuyển đổi thành **khung hình điện thoại Smartphone** (có Dynamic Island, thanh điều hướng dưới đáy Mobile Bottom Nav, bo góc chuẩn iOS/Android).
   - Hoặc thu nhỏ cửa sổ trình duyệt / mở trên điện thoại thực tế: Hệ thống tự động kích hoạt giao diện Responsive dạng Native App hoàn hảo!

