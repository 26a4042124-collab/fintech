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
    users = load_users()
    for user in users:
        u = user['username'].strip().lower()
        p = user.get('phone', '').strip()
        if (u == username.strip().lower() or p == username.strip()) and user['password'] == password:
            return {
                "success": True,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "email": user.get("email", ""),
                    "phone": user.get("phone", ""),
                    "occupation": user.get("occupation", "Cá nhân"),
                    "monthly_income": user.get("monthly_income", 18000000),
                    "connected_banks": user.get("connected_banks", []),
                    "goals": user.get("goals", []),
                    "avatar_initial": user["full_name"][0].upper() if user.get("full_name") else "U"
                }
            }
    return {"success": False, "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"}

def register_user(phone, full_name, email, password, goals=None):
    users = load_users()
    # Kiểm tra trùng số điện thoại hoặc email
    for user in users:
        if user.get('phone', '').strip() == phone.strip():
            return {"success": False, "message": "Số điện thoại này đã được đăng ký!"}
        if user.get('email', '').strip().lower() == email.strip().lower():
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
        "connected_banks": [],
        "goals": goals or []
    }
    users.append(new_user)
    save_users(users)
    return {"success": True, "user": new_user}

def user_exists_by_phone(phone):
    users = load_users()
    return any(u.get('phone', '').strip() == phone.strip() for u in users)
