# Hướng dẫn cài đặt và chạy SQLite

Tài liệu này hướng dẫn mỗi thành viên tạo CSDL SQLite riêng từ dữ liệu mẫu. Không chia sẻ `data/finlab.db` hoặc `.env` qua GitHub.

## Yêu cầu

- Python 3.10 trở lên
- Git
- Terminal tại thư mục gốc của dự án

## 1. Lấy mã nguồn và cài dependencies

```powershell
git clone <repository-url>
Set-Location fintech
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu đã có bản clone, dùng `git pull` thay cho `git clone`.

## 2. Tạo cấu hình môi trường

Trên Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Mở `.env`, đặt các giá trị bí mật riêng cho máy này. Tạo Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Tạo secret ngẫu nhiên cho HMAC và Flask:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Chạy lệnh thứ hai hai lần, rồi điền lần lượt vào `FINLAB_ACCOUNT_HMAC_KEY` và `FLASK_SECRET_KEY`. Điền kết quả Fernet vào `FINLAB_CRYPTO_KEY`. Giữ nguyên `FINLAB_DATABASE_URL=sqlite:///data/finlab.db`.

Không gửi `.env` cho người khác, không đưa khóa vào mã nguồn. Nếu cần giải mã dữ liệu đã mã hóa, phải giữ lại Fernet key đã dùng để tạo dữ liệu đó.

## 3. Tạo CSDL từ dữ liệu JSON

Chạy một lần tại thư mục gốc dự án:

```powershell
python migrate_json_to_sql.py
```

Kết quả mong đợi cho bộ baseline:

- `users: 4`
- `transactions: 35`
- `baseline_net: 4451000`
- `baseline_wallet_balance: 4451000`

`mock_transactions_3months.json` là bộ dữ liệu thay thế và không được cộng vào baseline 35 giao dịch. Script từ chối nhập đè CSDL đã có dữ liệu. Không chạy lại trên CSDL đang sử dụng.

## 4. Khởi chạy ứng dụng

```powershell
python app.py
```

Mở địa chỉ Flask hiển thị trong Terminal. Tài khoản demo nằm trong dữ liệu mẫu của dự án.

## 5. Xem và truy vấn bảng trong VS Code

Sau khi cài extension SQLite:

1. Mở Command Palette bằng `Ctrl+Shift+P`.
2. Chạy `SQLite: Open Database` và chọn `data\finlab.db`.
3. Chạy `SQLite: New Query`.
4. Nếu cần, chạy `SQLite: Use Database` và chọn `finlab.db`.
5. Viết truy vấn rồi chạy `SQLite: Run Query`.

Ví dụ:

```sql
SELECT id, timestamp, type, amount, description
FROM transactions
ORDER BY timestamp DESC
LIMIT 20;
```

Mỗi thành viên tạo CSDL riêng trên máy mình. Không commit `data/finlab.db`, `.env`, hoặc dữ liệu cá nhân thật lên GitHub.
