import json
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def authenticate_user(username, password):
    """
    Xác thực tài khoản người dùng
    """
    users = load_users()
    for user in users:
        if user['username'].strip().lower() == username.strip().lower() and user['password'] == password:
            return {
                "success": True,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                    "occupation": user.get("occupation", "Cá nhân"),
                    "monthly_income": user.get("monthly_income", 18000000),
                    "connected_banks": user.get("connected_banks", [])
                }
            }
    return {"success": False, "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"}
