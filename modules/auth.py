import json
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def authenticate_user(username, password):
    """
    Xác thực người dùng linh hoạt:
    - Hỗ trợ đăng nhập bằng: Username, Email, hoặc Số điện thoại.
    - Hỗ trợ kiểm tra mật khẩu chính xác.
    - Chế độ Test: nếu để trống mật khẩu hoặc là tài khoản demo, cho phép đăng nhập để kiểm thử mượt mà.
    """
    if not username:
        return {"success": False, "message": "Vui lòng nhập Email, Số điện thoại hoặc Tên đăng nhập!"}

    ident = username.strip().lower()
    pwd = (password or '').strip()
    users = load_users()

    # Tìm user khớp theo username, email hoặc phone
    matched_user = None
    for user in users:
        u_name = user.get('username', '').strip().lower()
        u_mail = user.get('email', '').strip().lower()
        u_phone = user.get('phone', '').strip().lower()

        if ident in (u_name, u_mail, u_phone):
            matched_user = user
            break

    if matched_user:
        stored_pwd = matched_user.get('password', '')
        # Kiểm tra mật khẩu:
        # 1. Khớp chính xác mật khẩu
        # 2. Hoặc người dùng không nhập mật khẩu (chế độ test/bypass nhanh)
        # 3. Hoặc nhập password demo mặc định
        if not pwd or pwd == stored_pwd or pwd in ('password123', '123', '123456', 'admin'):
            return {
                "success": True,
                "user": {
                    "id": matched_user["id"],
                    "username": matched_user["username"],
                    "full_name": matched_user["full_name"],
                    "email": matched_user.get("email", ""),
                    "phone": matched_user.get("phone", ""),
                    "occupation": matched_user.get("occupation", "Cá nhân"),
                    "monthly_income": matched_user.get("monthly_income", 18000000),
                    "connected_banks": matched_user.get("connected_banks", []),
                    "goals": matched_user.get("goals", []),
                    "avatar_initial": matched_user["full_name"][0].upper() if matched_user.get("full_name") else "U"
                }
            }
        else:
            return {"success": False, "message": "Mật khẩu không chính xác. Vui lòng thử lại!"}

    # Nếu không tìm thấy trong users.json nhưng người dùng nhập 'demo' hoặc 'admin'
    if ident in ('demo', 'admin', 'test', 'nguyen_van_a'):
        first_user = users[0] if users else {
            "id": "usr_001",
            "username": "nguyen_van_a",
            "full_name": "Nguyễn Văn A",
            "email": "nguyenvana@gmail.com",
            "phone": "0912345678",
            "occupation": "Nhân viên văn phòng",
            "monthly_income": 18000000,
            "connected_banks": ["Vietcombank", "Techcombank", "MB Bank"],
            "goals": []
        }
        return {
            "success": True,
            "user": {
                "id": first_user["id"],
                "username": first_user["username"],
                "full_name": first_user["full_name"],
                "email": first_user.get("email", ""),
                "phone": first_user.get("phone", ""),
                "occupation": first_user.get("occupation", "Cá nhân"),
                "monthly_income": first_user.get("monthly_income", 18000000),
                "connected_banks": first_user.get("connected_banks", []),
                "goals": first_user.get("goals", []),
                "avatar_initial": first_user["full_name"][0].upper() if first_user.get("full_name") else "U"
            }
        }

    return {"success": False, "message": "Không tìm thấy tài khoản với thông tin đã nhập!"}

def register_user(phone, full_name, email, password, goals=None):
    users = load_users()
    # Kiểm tra trùng số điện thoại hoặc email
    for user in users:
        if phone and user.get('phone', '').strip() == phone.strip():
            return {"success": False, "message": "Số điện thoại này đã được đăng ký!"}
        if email and user.get('email', '').strip().lower() == email.strip().lower():
            return {"success": False, "message": "Email này đã được đăng ký!"}

    new_id = f"usr_{str(len(users) + 1).zfill(3)}"
    # Tạo username từ tên
    username_base = full_name.lower().replace(" ", "_")
    import unicodedata
    username_base = unicodedata.normalize('NFD', username_base)
    username_base = ''.join(c for c in username_base if unicodedata.category(c) != 'Mn')
    username = username_base
    counter = 1
    existing_usernames = {u['username'] for u in users}
    while username in existing_usernames:
        username = f"{username_base}_{counter}"
        counter += 1

    new_user = {
        "id": new_id,
        "username": username,
        "password": password,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "occupation": "Cá nhân",
        "monthly_income": 18000000,
        "connected_banks": ["Vietcombank", "Techcombank"],
        "goals": goals or []
    }
    users.append(new_user)
    save_users(users)
    return {"success": True, "user": new_user}

def user_exists_by_phone(phone):
    users = load_users()
    return any(u.get('phone', '').strip() == phone.strip() for u in users)
