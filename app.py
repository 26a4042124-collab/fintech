import os
import sys
import time
import json
import socket
import io
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Load .env TRƯỚC KHI import bất cứ thứ gì khác
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import qrcode
from modules.auth import (
    authenticate_user, 
    register_user, 
    user_exists_by_phone,
    get_user_by_id, 
    get_all_users, 
    update_user_field, 
    reset_user_password, 
    set_user_role, 
    toggle_user_status,
    sanitize_user,
    admin_required
)
from modules.audit_logger import log_action, get_audit_logs, load_audit_logs
from modules.open_banking import (
    get_available_banks, 
    fetch_open_banking_transactions, 
    simulate_bank_connection
)
from modules.ai_categorizer import process_all_transactions, load_categories, save_categories
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response
from modules.otp_service import generate_otp, send_otp_email, verify_otp

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'finlab_canva_redesign_secret_2026')

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'system_settings.json')
AUDIT_FILE = os.path.join(os.path.dirname(__file__), 'data', 'audit_logs.json')

def load_system_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {
            "app_name": "FinLab PFM & Open Banking",
            "app_version": "v2.5 Enterprise",
            "currency": "VNĐ",
            "date_format": "DD/MM/YYYY",
            "session_timeout_minutes": 60,
            "min_password_length": 6,
            "open_banking_sandbox": True,
            "compliance_standard": "Nghị định 13/2023/NĐ-CP & Thông tư 64/2024/TT-NHNN"
        }
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_system_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_current_user():
    if 'user' not in session:
        return None
    user_id = session['user'].get('id')
    db_user = get_user_by_id(user_id)
    if db_user:
        sanitized = sanitize_user(db_user)
        session['user'] = sanitized
        return sanitized
    return session['user']

# ==========================================================================
# Helpers & Auth Functions
# ==========================================================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_financial_data():
    user = session.get('user', {})
    monthly_income = user.get('monthly_income', 18000000)
    raw_txns = fetch_open_banking_transactions()
    custom_txns = session.get('custom_transactions', [])
    all_txns = list(custom_txns) + list(raw_txns)
    enriched_txns = process_all_transactions(all_txns)
    enriched_txns_sorted = sorted(enriched_txns, key=lambda x: x.get('timestamp', ''), reverse=True)
    health_data = compute_financial_health(enriched_txns, total_income=monthly_income)
    return enriched_txns_sorted, health_data

# ==========================================================================
# 1. Landing / Onboarding
# ==========================================================================
@app.route('/')
def landing():
    # User requirement: truy cập link là vào thẳng trang login
    return redirect(url_for('login'))

@app.route('/landing')
def landing_page():
    return render_template('landing.html')

# ==========================================================================
# 2. Register Flow
# ==========================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    error = None
    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            error = 'Vui lòng nhập địa chỉ email hợp lệ!'
        else:
            # Sinh OTP và gửi email
            otp = generate_otp()
            result = send_otp_email(email, otp)
            if result['success']:
                session['reg_email_contact'] = email
                session['reg_otp_code']      = otp
                session['reg_otp_created_at'] = time.time()
                return redirect(url_for('register_otp'))
            else:
                # Nếu chưa cấu hình mail, vẫn cho qua nhưng hiện cảnh báo
                import os as _os
                if not _os.environ.get('MAIL_SENDER'):
                    # Dev mode: bypass, hiện OTP trên flash
                    session['reg_email_contact'] = email
                    session['reg_otp_code']      = otp
                    session['reg_otp_created_at'] = time.time()
                    session['dev_otp_hint']       = otp   # chỉ hiện ở dev
                    return redirect(url_for('register_otp'))
                error = f'Không thể gửi email: {result["error"]}'
    return render_template('register.html', error=error, email=email)

@app.route('/register/otp', methods=['GET', 'POST'])
def register_otp():
    if 'reg_email_contact' not in session:
        return redirect(url_for('register'))
    error = None
    if request.method == 'POST':
        action = request.form.get('action', 'verify')
        # Gửi lại OTP
        if action == 'resend':
            otp = generate_otp()
            email = session['reg_email_contact']
            result = send_otp_email(email, otp)
            session['reg_otp_code']       = otp
            session['reg_otp_created_at'] = time.time()
            session.pop('dev_otp_hint', None)
            if result['success']:
                session['resend_success'] = True
            elif not os.environ.get('MAIL_SENDER'):
                session['dev_otp_hint'] = otp
            return redirect(url_for('register_otp'))
        # Xác minh OTP
        otp_input = request.form.get('otp', '').strip()
        stored_otp = session.get('reg_otp_code', '')
        created_at = session.get('reg_otp_created_at', 0)
        result = verify_otp(stored_otp, created_at, otp_input)
        if result['valid']:
            session['reg_otp_verified'] = True
            session.pop('dev_otp_hint', None)
            session.pop('resend_success', None)
            return redirect(url_for('register_create'))
        else:
            error = result['reason']

    email        = session.get('reg_email_contact', '')
    dev_hint     = session.pop('dev_otp_hint', None)
    resend_ok    = session.pop('resend_success', False)
    mail_configured = bool(os.environ.get('MAIL_SENDER'))
    return render_template('register_otp.html',
        contact=email,
        contact_type='email',
        error=error,
        dev_hint=dev_hint,
        resend_ok=resend_ok,
        mail_configured=mail_configured
    )

@app.route('/register/create', methods=['GET', 'POST'])
def register_create():
    if not session.get('reg_otp_verified'):
        return redirect(url_for('register'))
    error = None
    form_data = {}
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        form_data = {'full_name': full_name, 'email': email}
        if not full_name:
            error = 'Vui lòng nhập họ và tên!'
        elif not email or '@' not in email:
            error = 'Email không hợp lệ!'
        elif len(password) < 6:
            error = 'Mật khẩu phải có ít nhất 6 ký tự!'
        elif password != confirm:
            error = 'Mật khẩu xác nhận không khớp!'
        else:
            session['reg_full_name'] = full_name
            session['reg_email'] = email
            session['reg_password'] = password
            return redirect(url_for('register_goals'))
    # Pre-fill email từ bước nhập contact
    prefill_email = session.get('reg_email_contact', '')
    form_data.setdefault('email', prefill_email)
    return render_template('register_create.html', error=error, form_data=form_data)

@app.route('/register/goals', methods=['GET', 'POST'])
def register_goals():
    if not session.get('reg_otp_verified'):
        return redirect(url_for('register'))
    if request.method == 'POST':
        goals = request.form.getlist('goals')
        phone = session.get('reg_phone', '')
        full_name = session.get('reg_full_name', '')
        email = session.get('reg_email', '')
        password = session.get('reg_password', '')
        result = register_user(phone, full_name, email, password, goals)
        # Xóa session đăng ký
        for key in ['reg_phone', 'reg_otp_verified', 'reg_full_name', 'reg_email', 'reg_password']:
            session.pop(key, None)
        if result['success']:
            session['register_success'] = True
            return redirect(url_for('login'))
        else:
            return render_template('register_goals.html', error=result['message'])
    return render_template('register_goals.html', error=None)

# ==========================================================================
# 3. Login / Logout
# ==========================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Cho phép truy cập thẳng vào trang login hoặc chuyển tiếp nếu user bấm tiếp tục
    if request.args.get('continue') and 'user' in session:
        if session['user'].get('role') == 'admin':
            return redirect(url_for('admin_overview'))
        return redirect(url_for('dashboard'))

    error = None
    username = ''
    register_success = session.pop('register_success', False)
    current_session_user = session.get('user')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        auth_result = authenticate_user(username, password)
        if auth_result.get('success'):
            user_data = auth_result['user']
            session['user'] = user_data
            
            action_label = "Đăng nhập Admin" if user_data.get('role') == 'admin' else "Đăng nhập User"
            log_action(
                actor=user_data['username'],
                action=action_label,
                target="Hệ thống FinLab",
                result="Success",
                details=f"Người dùng đăng nhập thành công vào vai trò {user_data.get('role', 'user').upper()}",
                ip=request.remote_addr or "127.0.0.1"
            )
            
            if user_data.get('role') == 'admin':
                return redirect(url_for('admin_overview'))
            return redirect(url_for('dashboard'))
        else:
            error = auth_result.get('message', 'Thông tin đăng nhập không chính xác!')
            log_action(
                actor=username or "anonymous",
                action="Đăng nhập thất bại",
                target="Hệ thống FinLab",
                result="Failed",
                details=error,
                ip=request.remote_addr or "127.0.0.1"
            )
            
    return render_template('login.html', 
        error=error, 
        username=username, 
        register_success=register_success,
        current_session_user=current_session_user
    )

@app.route('/logout')
def logout():
    user = session.get('user', {})
    if user:
        log_action(
            actor=user.get('username', 'user'),
            action="Đăng xuất",
            target="Hệ thống FinLab",
            result="Success",
            details="Người dùng đăng xuất khỏi phiên làm việc",
            ip=request.remote_addr or "127.0.0.1"
        )
    session.clear()
    return redirect(url_for('landing'))

# ==========================================================================
# 4. Dashboard
# ==========================================================================
@app.route('/dashboard')
@login_required
def dashboard():
    user = session['user']
    enriched_txns, health_data = get_financial_data()
    banks = get_available_banks()
    balance = health_data.get('income', 0) - health_data.get('total_expense', 0)
    return render_template('dashboard.html',
        user=user,
        transactions=enriched_txns[:5],
        health=health_data,
        banks=banks,
        balance=balance
    )

# ==========================================================================
# 3. ADMIN PORTAL (SIDEBAR LAYOUT & 5 TRANG QUẢN TRỊ CHUẨN FINTECH)
# ==========================================================================

# TRANG 1 — ADMIN OVERVIEW (DASHBOARD)
@app.route('/admin')
@app.route('/admin/overview')
@admin_required
def admin_overview():
    user = get_current_user()
    all_users = get_all_users()
    total_users_count = len(all_users)
    active_users_count = len([u for u in all_users if u.get('status') == 'active'])
    locked_users_count = len([u for u in all_users if u.get('status') == 'locked'])
    
    # Thống kê phân bổ ngân hàng
    bank_counts = {}
    for u in all_users:
        for b in u.get('connected_banks', []):
            bank_counts[b] = bank_counts.get(b, 0) + 1
            
    categories = load_categories()
    total_categories_count = len([c for c in categories if not c.get('is_hidden', False)])
    
    all_logs = load_audit_logs()
    total_events_count = len(all_logs)
    recent_logs = get_audit_logs(limit=5)
    
    return render_template(
        'admin/overview.html',
        active_page='overview',
        admin_user=user,
        total_users=total_users_count,
        active_users=active_users_count,
        locked_users=locked_users_count,
        total_categories=total_categories_count,
        total_events=total_events_count,
        bank_counts=bank_counts,
        recent_logs=recent_logs
    )

# TRANG 2 — USER MANAGEMENT
@app.route('/admin/users')
@admin_required
def admin_users():
    user = get_current_user()
    all_users = get_all_users()
    return render_template(
        'admin/users.html',
        active_page='users',
        admin_user=user,
        users=all_users
    )

# TRANG 3 — CATEGORY MANAGEMENT
@app.route('/admin/categories')
@admin_required
def admin_categories():
    user = get_current_user()
    categories = load_categories()
    return render_template(
        'admin/categories.html',
        active_page='categories',
        admin_user=user,
        categories=categories
    )

# TRANG 4 — AUDIT LOGS
@app.route('/admin/audit-logs')
@admin_required
def admin_audit_logs():
    user = get_current_user()
    action_filter = request.args.get('action', 'ALL')
    logs = get_audit_logs(limit=200, action_filter=action_filter)
    return render_template(
        'admin/audit_logs.html',
        active_page='audit_logs',
        admin_user=user,
        logs=logs
    )

# TRANG 5 — SYSTEM SETTINGS
@app.route('/admin/settings')
@admin_required
def admin_settings():
    user = get_current_user()
    settings = load_system_settings()
    return render_template(
        'admin/settings.html',
        active_page='settings',
        admin_user=user,
        settings=settings
    )

# ==========================================================================
# 4. ADMIN REST APIS
# ==========================================================================

@app.route('/admin/api/users/<user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_api_toggle_status(user_id):
    admin = get_current_user()
    new_status, message = toggle_user_status(user_id, admin_user=admin)
    if new_status:
        return jsonify({"success": True, "new_status": new_status, "message": message})
    return jsonify({"success": False, "message": message}), 400

@app.route('/admin/api/users/<user_id>/role', methods=['POST'])
@admin_required
def admin_api_change_role(user_id):
    admin = get_current_user()
    data = request.get_json() or {}
    new_role = data.get('role', 'user')
    
    success, message = set_user_role(user_id, new_role, admin_user=admin)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "message": message}), 400

@app.route('/admin/api/users/<user_id>/reset-password', methods=['POST'])
@admin_required
def admin_api_reset_password(user_id):
    admin = get_current_user()
    data = request.get_json() or {}
    new_pwd = data.get('password', 'password123')
    
    success, message = reset_user_password(user_id, new_pwd, admin_user=admin)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "message": message}), 400

@app.route('/admin/api/categories', methods=['POST'])
@admin_required
def admin_api_add_category():
    admin = get_current_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    cat_type = data.get('type', 'EXPENSE')
    bucket = data.get('bucket', 'WANTS')
    icon = data.get('icon', 'fa-tag').strip()
    color = data.get('color', '#6366f1')
    keywords = data.get('keywords', [])
    
    if not name:
        return jsonify({"success": False, "message": "Vui lòng nhập tên danh mục!"}), 400
        
    categories = load_categories()
    new_id = f"cat_custom_{int(time.time()*1000)%1000000}"
    
    new_cat = {
        "id": new_id,
        "name": name,
        "type": cat_type,
        "bucket": bucket,
        "icon": icon,
        "color": color,
        "is_default": False,
        "is_hidden": False,
        "keywords": keywords if isinstance(keywords, list) else [keywords]
    }
    
    categories.append(new_cat)
    save_categories(categories)
    
    log_action(
        actor=admin.get('username', 'admin'),
        action="Thêm danh mục",
        target=f"{name} ({new_id})",
        result="Success",
        details=f"Tạo mới danh mục {cat_type} - Rổ {bucket}"
    )
    
    return jsonify({"success": True, "message": f"Đã thêm danh mục '{name}' thành công!", "category": new_cat})

@app.route('/admin/api/categories/<cat_id>', methods=['POST', 'PUT'])
@admin_required
def admin_api_update_category(cat_id):
    admin = get_current_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    cat_type = data.get('type', 'EXPENSE')
    bucket = data.get('bucket', 'WANTS')
    icon = data.get('icon', 'fa-tag').strip()
    color = data.get('color', '#6366f1')
    keywords = data.get('keywords', [])
    
    categories = load_categories()
    found = False
    
    for i, c in enumerate(categories):
        if c.get('id') == cat_id:
            categories[i]['name'] = name or categories[i]['name']
            categories[i]['type'] = cat_type
            categories[i]['bucket'] = bucket
            categories[i]['icon'] = icon
            categories[i]['color'] = color
            categories[i]['keywords'] = keywords if isinstance(keywords, list) else [keywords]
            found = True
            break
            
    if not found:
        return jsonify({"success": False, "message": "Không tìm thấy danh mục!"}), 404
        
    save_categories(categories)
    log_action(
        actor=admin.get('username', 'admin'),
        action="Chỉnh sửa danh mục",
        target=f"{name} ({cat_id})",
        result="Success",
        details="Cập nhật thông tin và từ khóa ánh xạ NLP"
    )
    
    return jsonify({"success": True, "message": f"Đã cập nhật danh mục '{name}' thành công!"})

@app.route('/admin/api/categories/<cat_id>/toggle-hidden', methods=['POST'])
@admin_required
def admin_api_toggle_hide_category(cat_id):
    admin = get_current_user()
    categories = load_categories()
    cat_name = cat_id
    new_hidden_state = False
    found = False
    
    for i, c in enumerate(categories):
        if c.get('id') == cat_id:
            c['is_hidden'] = not c.get('is_hidden', False)
            new_hidden_state = c['is_hidden']
            cat_name = c.get('name', cat_id)
            found = True
            break
            
    if not found:
        return jsonify({"success": False, "message": "Không tìm thấy danh mục!"}), 404
        
    save_categories(categories)
    action_str = "Ẩn danh mục" if new_hidden_state else "Hiện danh mục"
    log_action(
        actor=admin.get('username', 'admin'),
        action=action_str,
        target=f"{cat_name} ({cat_id})",
        result="Success",
        details=f"Chuyển trạng thái hiển thị của danh mục sang {'Ẩn' if new_hidden_state else 'Hiện'}"
    )
    
    return jsonify({
        "success": True, 
        "is_hidden": new_hidden_state,
        "message": f"Đã {action_str.lower()} '{cat_name}' thành công!"
    })

@app.route('/admin/api/settings', methods=['POST'])
@admin_required
def admin_api_save_settings():
    admin = get_current_user()
    data = request.get_json() or {}
    current = load_system_settings()
    
    current['app_name'] = data.get('app_name', current.get('app_name'))
    current['currency'] = data.get('currency', current.get('currency'))
    current['date_format'] = data.get('date_format', current.get('date_format'))
    current['session_timeout_minutes'] = int(data.get('session_timeout_minutes', 60))
    current['min_password_length'] = int(data.get('min_password_length', 6))
    current['open_banking_sandbox'] = bool(data.get('open_banking_sandbox', True))
    
    save_system_settings(current)
    
    log_action(
        actor=admin.get('username', 'admin'),
        action="Lưu cài đặt hệ thống",
        target="Cấu hình FinLab",
        result="Success",
        details="Cập nhật các tham số cấu hình hệ thống"
    )
    
    return jsonify({"success": True, "message": "Đã lưu cài đặt hệ thống thành công!"})

@app.route('/admin/api/audit-logs/export')
@admin_required
def admin_api_export_audit_logs():
    if os.path.exists(AUDIT_FILE):
        return send_file(AUDIT_FILE, as_attachment=True, download_name="finlab_audit_logs.json")
    return jsonify({"error": "File not found"}), 404

# ==========================================================================
# 5. USER PFM REST APIS (CUSTOM RATIOS, GOALS, ROUND-UP, LIMITS, CONSENT)
# ==========================================================================

@app.route('/api/user/budget-ratio', methods=['POST'])
def api_update_budget_ratio():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    try:
        needs = int(data.get('needs', 50))
        wants = int(data.get('wants', 30))
        savings = int(data.get('savings', 20))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Dữ liệu tỷ lệ không hợp lệ!"}), 400
        
    if needs + wants + savings != 100:
        return jsonify({"success": False, "message": f"Tổng tỷ lệ phải đúng bằng 100% (Hiện tại là {needs + wants + savings}%)"}), 400
        
    if needs < 0 or wants < 0 or savings < 0:
        return jsonify({"success": False, "message": "Tỷ lệ không được âm!"}), 400
        
    user_id = session['user']['id']
    new_ratio = {"needs": needs, "wants": wants, "savings": savings}
    
    updated_user = update_user_field(user_id, 'budget_ratio', new_ratio)
    if updated_user:
        session['user'] = updated_user
        log_action(
            actor=updated_user['username'],
            action="Thay đổi tỷ lệ ngân sách",
            target="PFM Profile",
            result="Success",
            details=f"Thiết lập: {needs}% Thiết yếu - {wants}% Mong muốn - {savings}% Tiết kiệm"
        )
        return jsonify({
            "success": True, 
            "message": "Cập nhật tỷ lệ phân bổ ngân sách thành công!",
            "budget_ratio": new_ratio
        })
    return jsonify({"success": False, "message": "Lỗi lưu dữ liệu!"}), 500

@app.route('/api/goals', methods=['GET', 'POST'])
def api_goals():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    user = get_current_user()
    user_id = user['id']
    goals = user.get('savings_goals', [])
    
    if request.method == 'GET':
        return jsonify({"success": True, "goals": goals})
        
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    target_amount = data.get('target_amount', 0)
    current_amount = data.get('current_amount', 0)
    deadline = data.get('deadline', '')
    icon = data.get('icon', 'fa-piggy-bank')
    color = data.get('color', '#3b82f6')
    category = data.get('category', 'Mục tiêu')
    
    if not name or target_amount <= 0:
        return jsonify({"success": False, "message": "Vui lòng nhập tên mục tiêu và số tiền lớn hơn 0!"}), 400
        
    new_goal = {
        "id": f"goal_{int(time.time()*1000)%1000000}",
        "name": name,
        "target_amount": int(target_amount),
        "current_amount": int(current_amount),
        "deadline": deadline,
        "icon": icon,
        "color": color,
        "category": category
    }
    
    goals.append(new_goal)
    updated_user = update_user_field(user_id, 'savings_goals', goals)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Tạo mục tiêu tài chính",
        target=f"{name}",
        result="Success",
        details=f"Mục tiêu {int(target_amount):,.0f} VNĐ, hạn chót {deadline or 'Không giới hạn'}"
    )
    
    return jsonify({"success": True, "message": f"Đã tạo mục tiêu '{name}' thành công!", "goal": new_goal})

@app.route('/api/goals/<goal_id>/deposit', methods=['POST'])
def api_goal_deposit(goal_id):
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    amount = int(data.get('amount', 0))
    if amount <= 0:
        return jsonify({"success": False, "message": "Số tiền nạp phải lớn hơn 0!"}), 400
        
    user = get_current_user()
    goals = user.get('savings_goals', [])
    target_goal = None
    
    for g in goals:
        if g['id'] == goal_id:
            g['current_amount'] = g.get('current_amount', 0) + amount
            target_goal = g
            break
            
    if not target_goal:
        return jsonify({"success": False, "message": "Không tìm thấy mục tiêu!"}), 404
        
    updated_user = update_user_field(user['id'], 'savings_goals', goals)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Nạp tiền vào mục tiêu",
        target=f"{target_goal['name']}",
        result="Success",
        details=f"Nạp {amount:,.0f} VNĐ"
    )
    
    return jsonify({
        "success": True, 
        "message": f"Đã nạp thành công {amount:,.0f} VNĐ vào hũ '{target_goal['name']}'!",
        "goal": target_goal
    })

@app.route('/api/goals/<goal_id>', methods=['DELETE'])
def api_delete_goal(goal_id):
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    user = get_current_user()
    goals = user.get('savings_goals', [])
    filtered = [g for g in goals if g['id'] != goal_id]
    
    updated_user = update_user_field(user['id'], 'savings_goals', filtered)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Xóa mục tiêu tài chính",
        target=goal_id,
        result="Success",
        details="Xóa bỏ mục tiêu tiết kiệm"
    )
    
    return jsonify({"success": True, "message": "Đã xóa mục tiêu thành công!"})

@app.route('/api/user/round-up/config', methods=['POST'])
def api_round_up_config():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    user = get_current_user()
    current_cfg = user.get('round_up', {"enabled": True, "step": 10000, "accumulated_total": 0})
    
    if 'enabled' in data:
        current_cfg['enabled'] = bool(data['enabled'])
        update_user_field(user['id'], 'round_up_enabled', current_cfg['enabled'])
    if 'step' in data:
        step_val = int(data['step'])
        if step_val in [10000, 50000]:
            current_cfg['step'] = step_val
    if 'target_goal_id' in data:
        current_cfg['target_goal_id'] = data['target_goal_id']
        
    updated_user = update_user_field(user['id'], 'round_up', current_cfg)
    session['user'] = updated_user
    
    state_str = "Bật" if current_cfg['enabled'] else "Tắt"
    log_action(
        actor=user['username'],
        action="Cài đặt Heo đất làm tròn",
        target="Micro-investing",
        result="Success",
        details=f"{state_str} tính năng tích lũy tiền lẻ, bước: {current_cfg.get('step', 10000):,.0f}đ"
    )
    
    return jsonify({
        "success": True, 
        "message": "Cập nhật thiết lập Heo đất thành công!",
        "round_up": current_cfg
    })

@app.route('/api/user/round-up/transfer', methods=['POST'])
def api_round_up_transfer():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    target_goal_id = data.get('goal_id')
    user = get_current_user()
    
    round_up_cfg = user.get('round_up', {})
    acc_total = round_up_cfg.get('accumulated_total', 0)
    
    if acc_total <= 0:
        return jsonify({"success": False, "message": "Heo đất chưa có số dư để chuyển!"}), 400
        
    goals = user.get('savings_goals', [])
    target_goal = next((g for g in goals if g['id'] == target_goal_id), None) if target_goal_id else (goals[0] if goals else None)
    
    if target_goal:
        target_goal['current_amount'] = target_goal.get('current_amount', 0) + acc_total
        update_user_field(user['id'], 'savings_goals', goals)
        goal_name = target_goal['name']
    else:
        goal_name = "Quỹ tiết kiệm chung"
        
    round_up_cfg['accumulated_total'] = 0
    updated_user = update_user_field(user['id'], 'round_up', round_up_cfg)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Chuyển tiền lẻ Heo đất",
        target=goal_name,
        result="Success",
        details=f"Chuyển {acc_total:,.0f} VNĐ vào mục tiêu"
    )
    
    return jsonify({
        "success": True, 
        "message": f"Đã chuyển thành công {acc_total:,.0f} VNĐ từ Heo đất vào '{goal_name}'!",
        "accumulated_total": 0
    })

@app.route('/api/user/category-budgets', methods=['POST'])
def api_update_category_budgets():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    user = get_current_user()
    
    current_budgets = user.get('category_limits', user.get('category_budgets', {}))
    for cat, limit in data.items():
        try:
            val = int(limit)
            if val >= 0:
                current_budgets[cat] = val
        except Exception:
            pass
            
    update_user_field(user['id'], 'category_limits', current_budgets)
    updated_user = update_user_field(user['id'], 'category_budgets', current_budgets)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Cập nhật hạn mức chi tiêu",
        target="Hạn mức danh mục",
        result="Success",
        details=f"Cập nhật trần chi tiêu cho {len(data)} danh mục"
    )
    
    return jsonify({
        "success": True, 
        "message": "Đã lưu cài đặt hạn mức chi tiêu danh mục!",
        "category_budgets": current_budgets
    })

@app.route('/api/consent/toggle-scope', methods=['POST'])
def api_consent_toggle_scope():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    bank_id = data.get('bank_id')
    scope_key = data.get('scope')
    enabled = bool(data.get('enabled', True))
    
    user = get_current_user()
    consents = user.get('consents', [])
    updated = False
    bank_name = bank_id
    
    for c in consents:
        if c.get('bank_id') == bank_id:
            if 'scopes' not in c:
                c['scopes'] = {}
            c['scopes'][scope_key] = enabled
            updated = True
            bank_name = c.get('bank_name', bank_id)
            break
            
    if not updated:
        return jsonify({"success": False, "message": "Không tìm thấy ủy quyền cho ngân hàng này!"}), 404
        
    updated_user = update_user_field(user['id'], 'consents', consents)
    session['user'] = updated_user
    
    scope_labels = {
        "read_balance": "Xem số dư",
        "read_transactions": "Xem lịch sử giao dịch",
        "analyze_ai": "Phân tích AI PFM"
    }
    
    log_action(
        actor=user['username'],
        action="Thay đổi phạm vi quyền dữ liệu",
        target=bank_name,
        result="Success",
        details=f"{'Cấp quyền' if enabled else 'Tắt quyền'} '{scope_labels.get(scope_key, scope_key)}' (Nghị định 13)"
    )
    
    return jsonify({
        "success": True, 
        "message": f"Đã cập nhật quyền '{scope_labels.get(scope_key, scope_key)}' cho {bank_name}!",
        "consents": consents
    })

@app.route('/api/consent/revoke', methods=['POST'])
def api_consent_revoke():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    bank_id = data.get('bank_id')
    user = get_current_user()
    consents = user.get('consents', [])
    bank_name = bank_id
    
    for c in consents:
        if c.get('bank_id') == bank_id:
            c['status'] = 'REVOKED'
            bank_name = c.get('bank_name', bank_id)
            break
            
    updated_user = update_user_field(user['id'], 'consents', consents)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Thu hồi quyền truy cập (Revoke Consent)",
        target=bank_name,
        result="Success",
        details="Tạm ngừng chia sẻ dữ liệu Open Banking tuân thủ Nghị định 13/2023/NĐ-CP"
    )
    
    return jsonify({
        "success": True, 
        "message": f"Đã thu hồi quyền truy cập của {bank_name}!",
        "consents": consents
    })

@app.route('/api/consent/reauthorize', methods=['POST'])
def api_consent_reauthorize():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    bank_id = data.get('bank_id')
    user = get_current_user()
    consents = user.get('consents', [])
    bank_name = bank_id
    
    for c in consents:
        if c.get('bank_id') == bank_id:
            c['status'] = 'ACTIVE'
            c['granted_at'] = datetime.now().strftime("%Y-%m-%d")
            c['expires_at'] = "2026-12-31"
            c['scopes'] = {
                "read_balance": True,
                "read_transactions": True,
                "analyze_ai": True
            }
            bank_name = c.get('bank_name', bank_id)
            break
            
    updated_user = update_user_field(user['id'], 'consents', consents)
    session['user'] = updated_user
    
    log_action(
        actor=user['username'],
        action="Cấp lại quyền Open Banking",
        target=bank_name,
        result="Success",
        details="Cấp lại ủy quyền OAuth 2.0 hiệu lực 90 ngày"
    )
    
    return jsonify({
        "success": True, 
        "message": f"Cấp lại quyền thành công cho {bank_name}!",
        "consents": consents
    })

# ==========================================================================
# 5. Transactions
# ==========================================================================
@app.route('/transactions')
@login_required
def transactions():
    enriched_txns, health_data = get_financial_data()
    return render_template('transactions.html',
        user=session['user'],
        transactions=enriched_txns,
        health=health_data
    )


# ==========================================================================
# 5b. Add Transaction (Thêm giao dịch mới)
# ==========================================================================
@app.route('/add-transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        txn_type = request.form.get('type', 'OUTFLOW')
        amount_raw = request.form.get('amount', '0').replace('.', '').replace(',', '').replace('đ', '').replace('VND', '').strip()
        try:
            amount = float(amount_raw)
        except ValueError:
            amount = 0

        category = request.form.get('category', 'Khác').strip()
        bank = request.form.get('bank', 'Tiền mặt').strip()
        note = request.form.get('note', '').strip()
        txn_date = request.form.get('date', time.strftime('%Y-%m-%d')).strip()
        timestamp = f"{txn_date} {time.strftime('%H:%M:%S')}"

        if amount > 0:
            new_txn = {
                "id": f"TXN_{int(time.time()*1000)}",
                "timestamp": timestamp,
                "bank": bank,
                "account_number": "VÍ CÁ NHÂN",
                "type": txn_type,
                "amount": amount,
                "description": f"{category}: {note}" if note else category,
                "reference_code": f"APP.{int(time.time())}"
            }
            if 'custom_transactions' not in session:
                session['custom_transactions'] = []
            session['custom_transactions'] = [new_txn] + session['custom_transactions']
            session.modified = True
            return redirect(url_for('transactions', added='1'))

    today_str = time.strftime('%Y-%m-%d')
    return render_template('add_transaction.html', user=session['user'], today=today_str)

# ==========================================================================
# 5c. Wallets & Cards (Ví & Thẻ ngân hàng)
# ==========================================================================
@app.route('/wallets')
@login_required
def wallets():
    enriched_txns, health_data = get_financial_data()
    # Fix #3: Không truyền hardcoded wallets_data nữa.
    # Wallet cards được render hoàn toàn từ localStorage trên client (JS).
    # Server chỉ cung cấp recent_txns để hiển thị giao dịch gần đây.
    return render_template('wallets.html',
        user=session['user'],
        recent_txns=enriched_txns[:6]
    )

# ==========================================================================
# 5d. Budgets (Ngân sách chi tiêu)
# ==========================================================================
@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    enriched_txns, health_data = get_financial_data()
    cb = health_data.get('category_breakdown', {})

    budgets_list = [
        {
            "category": "Ăn uống & Cà phê",
            "icon": "utensils",
            "spent": cb.get("Ăn uống & Cà phê ngoài", 0) or 4200000,
            "limit": 5500000,
            "color": "#E8632A",
            "bg": "rgba(232, 99, 42, 0.12)"
        },
        {
            "category": "Đi lại & Xăng xe",
            "icon": "motorcycle",
            "spent": cb.get("Đi lại & Xăng xe", 0) or 950000,
            "limit": 1500000,
            "color": "#3B82F6",
            "bg": "rgba(59, 130, 246, 0.12)"
        },
        {
            "category": "Mua sắm cá nhân",
            "icon": "bag-shopping",
            "spent": cb.get("Mua sắm cá nhân", 0) or 3100000,
            "limit": 3000000,
            "color": "#EF4444",
            "bg": "rgba(239, 68, 68, 0.12)"
        },
        {
            "category": "Nhà cửa & Hóa đơn",
            "icon": "house",
            "spent": cb.get("Nhà ở & Hóa đơn tiện ích", 0) or 3500000,
            "limit": 4000000,
            "color": "#10B981",
            "bg": "rgba(16, 185, 129, 0.12)"
        },
        {
            "category": "Giải trí & Bạn bè",
            "icon": "film",
            "spent": cb.get("Giải trí & Phim ảnh", 0) or 1200000,
            "limit": 2000000,
            "color": "#8B5CF6",
            "bg": "rgba(139, 92, 246, 0.12)"
        },
        {
            "category": "Sức khỏe & Thuốc",
            "icon": "heart-pulse",
            "spent": cb.get("Y tế & Giáo dục", 0) or 350000,
            "limit": 1000000,
            "color": "#06B6D4",
            "bg": "rgba(6, 182, 212, 0.12)"
        }
    ]
    # Áp dụng các hạn mức do người dùng tự điều chỉnh (nếu có)
    custom_limits = session.get('custom_budget_limits', {})
    for b in budgets_list:
        if b['category'] in custom_limits:
            b['limit'] = float(custom_limits[b['category']])
    
    total_spent = sum(b['spent'] for b in budgets_list)
    total_limit = sum(b['limit'] for b in budgets_list)
    percent_spent = round((total_spent / total_limit) * 100) if total_limit > 0 else 0
    days_left = 11

    return render_template('budgets.html',
        user=session['user'],
        budgets=budgets_list,
        total_spent=total_spent,
        total_limit=total_limit,
        percent_spent=percent_spent,
        days_left=days_left
    )

@app.route('/api/budgets/update', methods=['POST'])
@login_required
def api_update_budget():
    data = request.get_json() or {}
    category = data.get('category')
    new_limit = data.get('limit')
    try:
        new_limit = float(new_limit)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Số tiền hạn mức không hợp lệ!"}), 400
    
    if 'custom_budget_limits' not in session:
        session['custom_budget_limits'] = {}
    session['custom_budget_limits'][category] = new_limit
    session.modified = True
    return jsonify({"success": True, "message": f"Đã cập nhật hạn mức danh mục '{category}' thành {new_limit:,.0f}đ!"})

# ==========================================================================
# 5e. Notifications (Thông báo)
# ==========================================================================
@app.route('/notifications')
@login_required
def notifications():
    notifications_data = [
        {
            "id": 1,
            "type": "alert",
            "icon": "fa-triangle-exclamation",
            "color": "#EF4444",
            "bg": "rgba(239, 68, 68, 0.12)",
            "title": "Cảnh báo vượt ngân sách",
            "body": "Bạn đã chi tiêu vượt hạn mức danh mục 'Mua sắm cá nhân' 100.000đ trong tháng 10.",
            "time": "10 phút trước",
            "unread": True
        },
        {
            "id": 2,
            "type": "reminder",
            "icon": "fa-receipt",
            "color": "#F59E0B",
            "bg": "rgba(245, 158, 11, 0.12)",
            "title": "Nhắc nhở thanh toán hóa đơn",
            "body": "Hóa đơn tiền điện VNPT/EVN hạn thanh toán ngày 25/10 (ước tính 680.000đ).",
            "time": "2 giờ trước",
            "unread": True
        },
        {
            "id": 3,
            "type": "inflow",
            "icon": "fa-circle-arrow-down",
            "color": "#10B981",
            "bg": "rgba(16, 185, 129, 0.12)",
            "title": "Biến động số dư +18.000.000đ",
            "body": "Tài khoản Vietcombank nhận lương tháng 09 từ CÔNG TY CP CÔNG NGHỆ ABC.",
            "time": "Hôm qua, 08:30",
            "unread": False
        },
        {
            "id": 4,
            "type": "goal",
            "icon": "fa-bullseye",
            "color": "#E8632A",
            "bg": "rgba(232, 99, 42, 0.12)",
            "title": "Tiến độ mục tiêu tài chính",
            "body": "Mục tiêu 'Quỹ khẩn cấp' đã đạt 30% kế hoạch. Tiếp tục phát huy nhé!",
            "time": "3 ngày trước",
            "unread": False
        }
    ]
    return render_template('notifications.html', user=session['user'], notifications=notifications_data)

# ==========================================================================
# 5f. Reports (Báo cáo thu chi đơn giản)
# ==========================================================================
@app.route('/reports')
@login_required
def reports():
    return redirect(url_for('analytics'))

# ==========================================================================
# 6. Analytics
# ==========================================================================
@app.route('/analytics')
@login_required
def analytics():
    enriched_txns, health_data = get_financial_data()
    return render_template('analytics.html',
        user=session['user'],
        transactions=enriched_txns,
        health=health_data
    )

# ==========================================================================
# 7. Goals
# ==========================================================================
@app.route('/goals')
@login_required
def goals():
    user = session['user']
    # Dữ liệu mục tiêu mẫu
    sample_goals = [
        {"id": 1, "name": "Quỹ khẩn cấp", "icon": "shield-halved", "target": 30000000, "current": 9000000, "color": "#FF6B35"},
        {"id": 2, "name": "Du lịch Đà Nẵng", "icon": "plane", "target": 10000000, "current": 3500000, "color": "#FFD700"},
        {"id": 3, "name": "Mua laptop mới", "icon": "laptop", "target": 25000000, "current": 15000000, "color": "#a855f7"},
    ]
    return render_template('goals.html', user=user, goals=sample_goals)

# ==========================================================================
# 8. Profile
# ==========================================================================
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=session['user'])

# ==========================================================================
# 9. API Routes
# ==========================================================================
@app.route('/api/sync-bank', methods=['POST'])
@login_required
def api_sync_bank():
    data = request.get_json() or {}
    bank_id = data.get('bank_id', 'VCB')
    result = simulate_bank_connection(bank_id)
    if result.get('success'):
        user = get_current_user()
        log_action(
            actor=user['username'],
            action="Đồng bộ Open Banking API",
            target=result.get('bank'),
            result="Success",
            details="Đồng bộ lịch sử giao dịch qua Open API v2.1"
        )
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"reply": "Xin vui lòng nhập câu hỏi của bạn!"})
    enriched_txns, health_data = get_financial_data()
    ai_reply = generate_chatbot_response(user_message, health_data)
    return jsonify({"reply": ai_reply})

@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    bank_filter = request.args.get('bank', 'ALL')
    raw_txns = fetch_open_banking_transactions(bank_filter)
    enriched = process_all_transactions(raw_txns)
    return jsonify({"total": len(enriched), "transactions": enriched})

# ==========================================================================

# ==========================================================================
# 11. Wallet API (localStorage-backed, session as fallback)
# ==========================================================================
@app.route('/api/wallets', methods=['GET'])
@login_required
def api_get_wallets():
    """Trả về danh sách ví của người dùng hiện tại từ session."""
    wallets_list = session.get('user_wallets', [])
    return jsonify({"success": True, "wallets": wallets_list})

@app.route('/api/wallets', methods=['POST'])
@login_required
def api_add_wallet():
    """Thêm ví mới vào danh sách."""
    data = request.get_json() or {}
    # Validate dữ liệu bắt buộc
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"success": False, "error": "Tên ví là bắt buộc!"}), 400
    balance_raw = data.get('initialBalance', 0)
    try:
        balance = float(balance_raw)
        if balance < 0:
            return jsonify({"success": False, "error": "Số dư không được âm!"}), 400
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Số dư không hợp lệ!"}), 400

    # Fix #1: Dùng client_id nếu có (để localStorage và session dùng cùng ID)
    # Client đã tạo ID duy nhất – server chấp nhận để tránh ID bị split
    client_id = (data.get('id') or '').strip()
    # Validate client_id: chỉ cho phép ký tự an toàn, không rỗng
    import re as _re
    if not client_id or not _re.match(r'^[A-Za-z0-9_\-]{1,64}$', client_id):
        client_id = f"W_{int(time.time()*1000)}"

    wallet = {
        "id": client_id,
        "name": name,
        "type": data.get('type', 'other'),
        "provider": (data.get('provider') or '').strip(),
        "initialBalance": balance,
        "currentBalance": balance,
        "managementMode": data.get('managementMode', 'manual'),
        "connectionStatus": "none",
        "note": (data.get('note') or '').strip(),
        "createdAt": data.get('createdAt') or time.strftime('%Y-%m-%dT%H:%M:%S'),
        "updatedAt": time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    if 'user_wallets' not in session:
        session['user_wallets'] = []
    # Ngăn trùng ID: nếu client_id đã tồn tại thì update thay vì thêm mới
    existing_ids = [w['id'] for w in session['user_wallets']]
    if client_id in existing_ids:
        session['user_wallets'] = [wallet if w['id'] == client_id else w
                                   for w in session['user_wallets']]
    else:
        session['user_wallets'] = session['user_wallets'] + [wallet]
    session.modified = True
    return jsonify({"success": True, "wallet": wallet}), 201

@app.route('/api/wallets/<wallet_id>', methods=['PUT'])
@login_required
def api_update_wallet(wallet_id):
    """Cập nhật thông tin ví."""
    data = request.get_json() or {}
    wallets_list = session.get('user_wallets', [])
    updated = None
    new_list = []
    for w in wallets_list:
        if w.get('id') == wallet_id:
            # Chỉ cho phép sửa các trường an toàn
            if 'name' in data:
                w['name'] = (data['name'] or '').strip()
            if 'type' in data:
                w['type'] = data['type']
            if 'provider' in data:
                w['provider'] = (data['provider'] or '').strip()
            if 'note' in data:
                w['note'] = (data['note'] or '').strip()
            if 'currentBalance' in data:
                try:
                    bal = float(data['currentBalance'])
                    if bal >= 0:
                        w['currentBalance'] = bal
                except (TypeError, ValueError):
                    pass
            w['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            updated = w
        new_list.append(w)
    if not updated:
        return jsonify({"success": False, "error": "Không tìm thấy ví!"}), 404
    session['user_wallets'] = new_list
    session.modified = True
    return jsonify({"success": True, "wallet": updated})

@app.route('/api/wallets/<wallet_id>', methods=['DELETE'])
@login_required
def api_delete_wallet(wallet_id):
    """Xóa ví theo ID."""
    wallets_list = session.get('user_wallets', [])
    new_list = [w for w in wallets_list if w.get('id') != wallet_id]
    if len(new_list) == len(wallets_list):
        return jsonify({"success": False, "error": "Không tìm thấy ví!"}), 404
    session['user_wallets'] = new_list
    session.modified = True
    return jsonify({"success": True})

# Fix #2: API chuyển tiền nội bộ
@app.route('/api/wallets/transfer', methods=['POST'])
@login_required
def api_transfer_wallet():
    """Chuyển tiền giữa 2 ví trong session."""
    data = request.get_json() or {}
    from_id = (data.get('fromId') or '').strip()
    to_id   = (data.get('toId')   or '').strip()
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        amount = 0

    if not from_id or not to_id:
        return jsonify({"success": False, "error": "Thiếu thông tin ví!"}), 400
    if from_id == to_id:
        return jsonify({"success": False, "error": "Ví nguồn và ví đích không được giống nhau!"}), 400
    if amount <= 0:
        return jsonify({"success": False, "error": "Số tiền phải lớn hơn 0!"}), 400

    wallets_list = session.get('user_wallets', [])
    from_w = next((w for w in wallets_list if w['id'] == from_id), None)
    to_w   = next((w for w in wallets_list if w['id'] == to_id),   None)
    if not from_w:
        return jsonify({"success": False, "error": "Không tìm thấy ví nguồn!"}), 404
    if not to_w:
        return jsonify({"success": False, "error": "Không tìm thấy ví đích!"}), 404
    if (float(from_w.get('currentBalance', 0)) < amount):
        return jsonify({"success": False, "error": f"Số dư ví '{from_w['name']}' không đủ!"}), 400

    from_w['currentBalance'] = float(from_w.get('currentBalance', 0)) - amount
    to_w['currentBalance']   = float(to_w.get('currentBalance',   0)) + amount
    from_w['updatedAt'] = to_w['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    session['user_wallets'] = wallets_list
    session.modified = True
    return jsonify({
        "success": True,
        "fromBalance": from_w['currentBalance'],
        "toBalance":   to_w['currentBalance'],
    })

# ==========================================================================
# 11. QR Code Endpoint - Tạo QR code để mở trên điện thoại
# ==========================================================================
@app.route('/qr')
def generate_qr_code():
    """Tạo QR code để điện thoại scan mở ứng dụng."""
    try:
        # Lấy IP address local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = 'localhost'
    
    port = int(os.environ.get('PORT', 5000))
    mobile_url = f'http://{local_ip}:{port}'
    
    # Tạo QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(mobile_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Chuyển hình ảnh thành bytes
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/mobile-access')
def mobile_access():
    """Trang hiển thị QR code để điện thoại scan."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = 'localhost'
    
    port = int(os.environ.get('PORT', 5000))
    mobile_url = f'http://{local_ip}:{port}'
    
    return render_template('mobile_qr.html', mobile_url=mobile_url, ip_address=local_ip, port=port)

# ==========================================================================
# 12. App Runner
# ==========================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Lấy IP address của máy tính
    import socket
    try:
        # Lấy IP address local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'
    
    print("=" * 75)
    print("🚀 FINLAB ENTERPRISE PFM & ADMIN PORTAL ĐANG KHỞI CHẠY...")
    print(f"")
    print(f"💻 Trên máy tính này:   http://127.0.0.1:{port}")
    print(f"📱 Trên điện thoại cùng WiFi: http://{local_ip}:{port}")
    print(f"")
    print(f"👉 Tài khoản User Demo:  nguyen_van_a | Mật khẩu: password123")
    print(f"👉 Tài khoản Admin Demo: admin        | Mật khẩu: admin123")
    print("=" * 75)
    app.run(host='0.0.0.0', port=port, debug=True)
