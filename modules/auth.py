import json
import os
import unicodedata
from functools import wraps
from flask import session, redirect, url_for, render_template

try:
    from modules.audit_logger import log_action
except ImportError:
    def log_action(*args, **kwargs):
        pass

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def sanitize_user(user):
    """
    Chuẩn hóa dữ liệu trả về cho session và frontend, tuyệt đối không lộ mật khẩu.
    """
    full_name = user.get("full_name", "").replace("(Verified)", "").strip()
    avatar_initial = full_name[0].upper() if full_name else "U"
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": full_name,
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": user.get("created_at", "2026-01-01"),
        "occupation": user.get("occupation", "Cá nhân"),
        "monthly_income": user.get("monthly_income", 18000000),
        "connected_banks": [c.get("bank_name") for c in user.get("consents", []) if c.get("status") == "ACTIVE" and c.get("bank_name")] or user.get("connected_banks", []),
        "goals": user.get("goals", []),
        "avatar_initial": avatar_initial,
        "budget_ratio": user.get("budget_ratio", {"needs": 50, "wants": 30, "savings": 20}),
        "savings_goals": user.get("savings_goals", []),
        "round_up_enabled": user.get("round_up_enabled", True),
        "round_up": user.get("round_up", {"enabled": True, "step": 10000, "accumulated_total": 0}),
        "category_limits": user.get("category_limits", user.get("category_budgets", {})),
        "category_budgets": user.get("category_budgets", user.get("category_limits", {})),
        "open_banking_consent": user.get("open_banking_consent", {"view_balance": True, "view_history": True, "ai_analytics": True}),
        "consents": user.get("consents", []),
        "wallets": user.get("wallets", []),
        "custom_transactions": user.get("custom_transactions", [])
    }

def authenticate_user(username, password):
    """
    Xác thực người dùng linh hoạt:
    - Hỗ trợ đăng nhập bằng: Username, Email, hoặc Số điện thoại.
    - Hỗ trợ kiểm tra trạng thái active / locked.
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
        user_status = matched_user.get("status", "active").lower()
        if user_status == "locked":
            log_action(
                actor=username,
                action="Đăng nhập tài khoản bị khóa",
                target=matched_user["id"],
                result="Failed",
                details="Người dùng thử đăng nhập nhưng tài khoản đang ở trạng thái locked"
            )
            return {
                "success": False,
                "message": "Tài khoản của bạn đã bị khóa bởi Quản trị viên. Vui lòng liên hệ ban quản trị FinLab!"
            }

        stored_pwd = matched_user.get('password', '')
        # Kiểm tra mật khẩu:
        # 1. Khớp chính xác mật khẩu
        # 2. Hoặc người dùng không nhập mật khẩu (chế độ test demo nhanh)
        # 3. Hoặc nhập password demo mặc định
        if not pwd or pwd == stored_pwd or pwd in ('password123', 'admin123', '123', '123456', 'admin'):
            log_action(
                actor=matched_user["username"],
                action="Đăng nhập thành công",
                target="FinLab App",
                result="Success",
                details=f"Đăng nhập qua định danh '{ident}'"
            )
            return {
                "success": True,
                "user": sanitize_user(matched_user)
            }
        else:
            log_action(
                actor=ident,
                action="Đăng nhập sai mật khẩu",
                target="FinLab App",
                result="Failed",
                details="Nhập mật khẩu không chính xác"
            )
            return {"success": False, "message": "Mật khẩu không chính xác. Vui lòng thử lại!"}

    # Nếu không tìm thấy nhưng gõ demo / admin
    if ident in ('demo', 'admin', 'test', 'nguyen_van_a'):
        first_user = users[0] if users else None
        if first_user:
            return {"success": True, "user": sanitize_user(first_user)}

    return {"success": False, "message": "Không tìm thấy tài khoản với thông tin đã nhập!"}

def register_user(phone, full_name, email, password, goals=None):
    users = load_users()
    for user in users:
        if phone and user.get('phone', '').strip() == phone.strip():
            return {"success": False, "message": "Số điện thoại này đã được đăng ký!"}
        if email and user.get('email', '').strip().lower() == email.strip().lower():
            return {"success": False, "message": "Email này đã được đăng ký!"}

    new_id = f"usr_{str(len(users) + 1).zfill(3)}"
    username_base = full_name.lower().replace(" ", "_")
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
        "role": "user",
        "status": "active",
        "created_at": "2026-10-23",
        "occupation": "Cá nhân",
        "monthly_income": 18000000,
        "connected_banks": ["Vietcombank", "Techcombank"],
        "goals": goals or []
    }
    users.append(new_user)
    save_users(users)
    return {"success": True, "user": sanitize_user(new_user)}

def user_exists_by_phone(phone):
    users = load_users()
    return any(u.get('phone', '').strip() == phone.strip() for u in users)

# ==========================================================================
# Admin Portal Support Functions
# ==========================================================================
def get_user_by_id(user_id):
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None

def get_all_users():
    """
    Dành cho Admin Portal: Lấy danh sách toàn bộ người dùng (đã lược bỏ mật khẩu).
    Tuân thủ Nghị định 13/2023/NĐ-CP.
    """
    users = load_users()
    return [sanitize_user(u) for u in users]

def update_user_field(user_id, field, value):
    users = load_users()
    updated = None
    for i, u in enumerate(users):
        if u["id"] == user_id:
            users[i][field] = value
            updated = users[i]
            break
    if updated:
        save_users(users)
        return sanitize_user(updated)
    return None

def update_user(user_id, updated_data):
    users = load_users()
    updated = None
    for i, u in enumerate(users):
        if u["id"] == user_id:
            for k, v in updated_data.items():
                users[i][k] = v
            updated = users[i]
            break
    if updated:
        save_users(users)
        return sanitize_user(updated)
    return None

def toggle_user_status(user_id, admin_user=None):
    """
    Khóa hoặc Mở khóa tài khoản (active <-> locked).
    Không cho phép khóa tài khoản chính mình nếu đang là admin.
    """
    users = load_users()
    for i, u in enumerate(users):
        if u["id"] == user_id:
            if admin_user and admin_user.get("id") == user_id:
                return None, "Bạn không thể tự khóa tài khoản của chính mình!"

            current = users[i].get("status", "active")
            new_status = "locked" if current == "active" else "active"
            users[i]["status"] = new_status
            save_users(users)

            action_name = "Khóa tài khoản" if new_status == "locked" else "Mở khóa tài khoản"
            log_action(
                actor=admin_user.get("username") if admin_user else "admin",
                action=action_name,
                target=f"{u['username']} ({u['id']})",
                result="Success",
                details=f"Chuyển trạng thái người dùng từ '{current}' sang '{new_status}'"
            )
            return new_status, f"Đã chuyển trạng thái tài khoản thành '{new_status}' thành công!"

    return None, "Không tìm thấy người dùng!"

def set_user_role(user_id, new_role, admin_user=None):
    if new_role not in ["admin", "user"]:
        return False, "Vai trò không hợp lệ!"

    if admin_user and admin_user.get("id") == user_id and new_role != "admin":
        return False, "Bạn không thể tự hạ quyền Quản trị viên của chính mình!"

    users = load_users()
    for i, u in enumerate(users):
        if u["id"] == user_id:
            old_role = users[i].get("role", "user")
            users[i]["role"] = new_role
            save_users(users)

            log_action(
                actor=admin_user.get("username") if admin_user else "admin",
                action="Thay đổi vai trò",
                target=f"{u['username']} ({u['id']})",
                result="Success",
                details=f"Đổi quyền từ '{old_role}' sang '{new_role}'"
            )
            return True, f"Đã cập nhật vai trò người dùng thành '{new_role}' thành công!"

    return False, "Không tìm thấy người dùng!"

def reset_user_password(user_id, new_password="password123", admin_user=None):
    users = load_users()
    for i, u in enumerate(users):
        if u["id"] == user_id:
            users[i]["password"] = new_password
            save_users(users)

            log_action(
                actor=admin_user.get("username") if admin_user else "admin",
                action="Đặt lại mật khẩu",
                target=f"{u['username']} ({u['id']})",
                result="Success",
                details=f"Mật khẩu của tài khoản {u['username']} đã được thiết lập lại"
            )
            return True, "Đặt lại mật khẩu thành công!"
    return False, "Không tìm thấy người dùng!"

# ==========================================================================
# Decorator Bảo mật @admin_required (RBAC Protection)
# ==========================================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        if session.get('user', {}).get('role') != 'admin':
            return render_template(
                'login.html', 
                error="Truy cập bị từ chối: Yêu cầu quyền Quản trị viên (Admin) để vào khu vực này!",
                username=session.get('user', {}).get('username')
            ), 403
        return f(*args, **kwargs)
    return decorated_function
