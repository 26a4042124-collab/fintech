# 🏦 FinLab - Nền Tảng Quản Lý Tài Chính Cá Nhân (PFM) & Open Banking Toàn Diện
> **Đồ án môn học: Công nghệ dịch vụ tài chính (FinTech)**  
> **Khoa Công nghệ Thông tin & Kinh tế số - Học viện Ngân hàng (HVNH)**

---

## 🌟 Giới thiệu Hệ thống FinLab

**FinLab** là nền tảng Quản lý tài chính cá nhân (Personal Financial Management - PFM) và Ngân hàng mở (Open Banking Aggregator) thông minh, giúp người dùng kiểm soát dòng tiền, ngăn chặn rò rỉ chi tiêu, thiết lập mục tiêu tài chính, tích lũy tiền lẻ tự động và tuân thủ chuẩn mực an ninh dữ liệu.

### 7 Tính Năng Nâng Cấp Toàn Diện:
1. **Tỷ Lệ Phân Bổ Ngân Sách Tùy Chọn (Custom Budget Ratio):** Chuyển đổi từ quy tắc 50/30/20 cứng nhắc thành hệ thống tùy biến linh hoạt theo từng giai đoạn cuộc sống (50/30/20, 60/20/20, 70/20/10 hoặc tự do kéo thanh trượt).
2. **Mục Tiêu Tài Chính Thông Minh (Savings Goals / Hũ Tích Lũy Số):** Theo dõi tiến độ tích lũy thực tế, AI dự báo số tháng hoàn thành dựa trên tốc độ dòng tiền (`months_needed`), cho phép nạp tiền nhanh vào từng hũ.
3. **Quy Tắc Làm Tròn Tiền Lẻ (Round-Up Savings / Micro-investing):** Giả lập cơ chế Heo Đất MoMo / Acorns, tự động gom tiền lẻ từ mọi giao dịch quẹt thẻ lên hàng 10.000đ hoặc 50.000đ để chuyển vào hũ tiết kiệm.
4. **Dự Báo Dòng Tiền Cuối Tháng (Cashflow Forecasting):** Thuật toán tính tốc độ đốt tiền trung bình mỗi ngày (`daily_burn_rate`), dự phóng tổng chi tiêu đến ngày 30, cảnh báo nguy cơ cạn ví hoặc thông báo thặng dư an toàn.
5. **Hạn Mức Chi Tiêu & Cảnh Báo Theo Danh Mục (Category Budget Alerts):** Đặt trần chi tiêu cho từng danh mục, hiển thị traffic light (Xanh < 80%, Vàng 80-99%, Đỏ >= 100% Vượt mức).
6. **Trung Tâm Quản Trị Quyền Dữ Liệu (Open Banking Consent Manager):** Tuân thủ **Nghị định 13/2023/NĐ-CP** (Bảo vệ dữ liệu cá nhân) & **Thông tư 64/2024/TT-NHNN** (Tiêu chuẩn Kỹ thuật Open API), cho phép bật/tắt quyền xem số dư, giao dịch, phân tích AI và Thu hồi ủy quyền (Revoke Consent).
7. **Phân Quyền RBAC & Trang Quản Trị Hệ Thống (Admin Dashboard):** Bảng điều khiển quản trị viên (`/admin`) với số liệu KPIs toàn hệ thống, biểu đồ phân bố ngân hàng & sức khỏe tài chính, bảng quản lý người dùng (đổi vai trò, đặt lại mật khẩu, khóa tài khoản) và bảng Nhật ký An ninh Hệ thống (Audit Logs).

---

## 📂 Cấu trúc Thư mục Dự án

```text
fintech/
├── app.py                      # Flask Backend: Routes, REST APIs, Session & RBAC
├── requirements.txt            # Danh sách thư viện Python (Flask)
├── README.md                   # Hướng dẫn chi tiết sử dụng & thuyết trình
│
├── data/                       # Dữ liệu JSON (Zero Database Dependency)
│   ├── users.json              # Danh sách tài khoản người dùng, cấu hình & consents
│   ├── mock_transactions.json  # Lịch sử giao dịch giả lập từ VCB, TCB, MB
│   └── audit_logs.json         # Nhật ký hệ thống & an ninh tuân thủ Nghị định 13
│
├── modules/                    # Các module nghiệp vụ fintech
│   ├── auth.py                 # Xác thực, phân quyền RBAC, user management & audit
│   ├── open_banking.py         # Giả lập Open Banking API, OAuth 2.0 & Consent check
│   ├── ai_categorizer.py       # AI NLP phân loại giao dịch & gắn nhãn rổ chi tiêu
│   ├── health_scoring.py       # Tính điểm sức khỏe, dự báo dòng tiền, hạn mức & heo đất
│   └── chatbot_ai.py           # Trợ lý ảo AI Chatbot tư vấn tài chính thông minh
│
├── static/                     # Tài nguyên giao diện tĩnh
│   ├── css/
│   │   └── style.css           # Design System Fintech cao cấp, Dark/Light hài hòa
│   └── js/
│       ├── main.js             # Xử lý tương tác giao diện, Chart.js & gọi REST APIs
│       └── chatbot.js          # Widget Trợ lý AI Chatbot
│
└── templates/                  # Giao diện HTML (Jinja2)
    ├── login.html              # Màn hình đăng nhập (có nút 1-chạm User & Admin)
    ├── dashboard.html          # Bảng điều khiển PFM người dùng toàn diện
    └── admin.html              # Bảng điều khiển Quản trị viên (Admin Portal)
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### Bước 1: Mở Terminal tại thư mục `fintech`
```bash
cd f:\amazing-noether\fintech
```

### Bước 2: Khởi chạy Server Flask
```bash
python app.py
```

Mở trình duyệt web và truy cập địa chỉ:  
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Tài khoản Đăng nhập Demo

Hệ thống có sẵn các nút **Đăng nhập 1-chạm** trên giao diện đăng nhập:

| Vai trò | Tên đăng nhập | Mật khẩu | Quyền hạn & Chức năng |
| :--- | :--- | :--- | :--- |
| **Người dùng (User)** | `nguyen_van_a` | `password123` | Bảng điều khiển PFM, Mục tiêu, Heo đất, Tỷ lệ tùy chọn, Chatbot |
| **Quản trị viên (Admin)** | `admin` | `admin123` | Truy cập `/admin`, Thống kê toàn hệ thống, Quản trị user & Audit logs |
| **Người dùng Test** | `demo` | `123` | Tài khoản Freelancer phụ |

---

## 💡 Kịch bản Demo Thuyết trình Chuẩn Chuyên gia FinTech

1. **Đăng nhập & RBAC:**
   - Đăng nhập tài khoản `nguyen_van_a` bằng nút 1-chạm.
   - Thử gõ đường dẫn `http://127.0.0.1:5000/admin` ➔ Hệ thống tự động chặn và hiển thị cảnh báo từ chối truy cập do thiếu quyền Admin.
2. **Dự báo Dòng tiền Cuối tháng (Tính năng 4):**
   - Chỉ vào Banner dự báo màu đỏ/xanh: Burn rate bình quân/ngày, dự kiến ngày cạn ví và số tiền thâm hụt cuối tháng.
3. **Mục tiêu Tài chính & Hũ Tích Lũy Số (Tính năng 2):**
   - Xem các mục tiêu: Quỹ khẩn cấp 3 tháng, Mua Laptop AI, Du lịch Đà Lạt.
   - Bấm **"+ Nạp thêm tiền tích lũy"** ➔ Nhập 1.000.000đ ➔ Xem thanh tiến độ % cập nhật realtime.
   - Bấm **"+ Tạo Mục Tiêu Mới"** để tạo hũ tích lũy mới.
4. **Tích lũy Tiền lẻ Heo Đất Micro-investing (Tính năng 3):**
   - Bật/tắt toggle "Tự động gom tiền lẻ".
   - Đổi mức làm tròn: 10.000đ hoặc 50.000đ.
   - Bấm nút **"Chuyển tiền lẻ vào Mục tiêu"** để kích hoạt dòng tiền tiết kiệm.
5. **Cơ cấu Ngân sách Tùy chọn (Tính năng 1):**
   - Bấm nút **"Tỷ lệ Ngân sách"** trên Navbar.
   - Chọn nhanh preset "Gia đình (60/20/20)" hoặc kéo thanh trượt ➔ Bấm "Lưu thiết lập" ➔ Điểm số và biểu đồ cập nhật ngay tức thì.
6. **Hạn mức Chi tiêu Danh mục (Tính năng 5):**
   - Xem bảng traffic light: Xanh (<80%), Vàng (80-99%), Đỏ (>100% Vượt mức).
   - Bấm **"Cài đặt Hạn mức"** để điều chỉnh trần chi tiêu.
7. **Trung tâm Quản trị Quyền & Consent (Tính năng 6):**
   - Bấm nút **"Quyền & Consent"** trên Navbar.
   - Xem thông tin tuân thủ **Nghị định 13/2023/NĐ-CP**.
   - Bật/tắt từng quyền (Xem số dư, Lịch sử, AI PFM) hoặc bấm **"Thu hồi quyền truy cập (Revoke Consent)"**.
8. **Trợ lý AI Chatbot:**
   - Mở chatbot ở góc dưới bên phải.
   - Bấm các gợi ý: *"Dự báo dòng tiền cuối tháng thế nào?"*, *"Tiền lẻ tích lũy Heo đất?"*, *"Tiến độ mục tiêu tài chính?"*.
9. **Trang Quản trị Admin (Tính năng 7):**
   - Đăng xuất và đăng nhập tài khoản `admin` / `admin123`.
   - Xem KPIs toàn hệ thống, 2 biểu đồ phân bố ngân hàng và sức khỏe tài chính.
   - Xem bảng Quản lý Người dùng (đổi role, reset mật khẩu, khóa tài khoản).
   - Xem bảng Nhật ký Hệ thống (Audit Logs) ghi nhận đầy đủ mọi thao tác vừa thực hiện.
