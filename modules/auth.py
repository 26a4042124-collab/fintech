import json
import os
from functools import wraps
from flask import session, redirect, url_for, render_template
from modules.audit_logger import log_action

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

def authenticate_user(username, password):
    """
    Xác thực tài khoản người dùng và kiểm tra trạng thái active / locked
    """
    users = load_users()
    for user in users:
        if user['username'].strip().lower() == username.strip().lower() and user['password'] == password:
            user_status = user.get("status", "active").lower()
            if user_status == "locked":
                log_action(
                    actor=username,
                    action="Đăng nhập tài khoản bị khóa",
                    target=user["id"],
                    result="Failed",
                    details="Người dùng thử đăng nhập nhưng tài khoản đang ở trạng thái locked"
                )
                return {
                    "success": False, 
                    "message": "Tài khoản của bạn đã bị khóa bởi Quản trị viên. Vui lòng liên hệ ban quản trị FinLab!"
                }
                
            return {
                "success": True,
                "user": sanitize_user(user)
            }
            
    return {"success": False, "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"}

def sanitize_user(user):
    """
    Chuẩn hóa dữ liệu trả về cho session và frontend, tuyệt đối không lộ mật khẩu.
    """
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": user.get("created_at", "2026-01-01"),
        "occupation": user.get("occupation", "Cá nhân"),
        "monthly_income": user.get("monthly_income", 18000000),
        "connected_banks": user.get("connected_banks", []),
        "budget_ratio": user.get("budget_ratio", {"needs": 50, "wants": 30, "savings": 20}),
        "savings_goals": user.get("savings_goals", []),
        "round_up_enabled": user.get("round_up_enabled", True),
        "round_up": user.get("round_up", {"enabled": True, "step": 10000, "accumulated_total": 0}),
        "category_limits": user.get("category_limits", user.get("category_budgets", {})),
        "category_budgets": user.get("category_budgets", user.get("category_limits", {})),
        "open_banking_consent": user.get("open_banking_consent", {"view_balance": True, "view_history": True, "ai_analytics": True}),
        "consents": user.get("consents", [])
    }

def get_user_by_id(user_id):
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None

def get_all_users():
    """
    Dành cho Admin Portal: Lấy danh sách toàn bộ người dùng (đã lược bỏ mật khẩu)
    Tuân thủ Nghị định 13/2023/NĐ-CP: Không trả về số dư hay giao dịch riêng tư.
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
    """
    Thay đổi vai trò người dùng (admin <-> user).
    Không cho phép tự hạ quyền admin của chính mình.
    """
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
