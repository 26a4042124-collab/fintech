import os
import sys
import time
import json
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from modules.auth import (
    authenticate_user, 
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

app = Flask(__name__)
app.secret_key = "finlab_open_banking_ai_secret_key_2026"

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
# 1. AUTHENTICATION & LOGIN/LOGOUT
# ==========================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        if session['user'].get('role') == 'admin':
            return redirect(url_for('admin_overview'))
        return redirect(url_for('dashboard'))
        
    error = None
    username = ""
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
            error = auth_result.get('message', 'Tên đăng nhập hoặc mật khẩu không đúng!')
            log_action(
                actor=username or "anonymous",
                action="Đăng nhập thất bại",
                target="Hệ thống FinLab",
                result="Failed",
                details=error,
                ip=request.remote_addr or "127.0.0.1"
            )
            
    return render_template('login.html', error=error, username=username)

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
    return redirect(url_for('login'))

# ==========================================================================
# 2. USER PFM DASHBOARD ROUTES
# ==========================================================================

@app.route('/')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    monthly_income = user.get('monthly_income', 18000000)
    budget_ratio = user.get('budget_ratio', {"needs": 50, "wants": 30, "savings": 20})
    savings_goals = user.get('savings_goals', [])
    round_up_config = user.get('round_up', {"enabled": True, "step": 10000, "accumulated_total": 0})
    category_budgets = user.get('category_limits', user.get('category_budgets', {}))
    consents = user.get('consents', [])
    
    # 1. Đọc dữ liệu Open Banking (kiểm tra consent tuân thủ Nghị định 13)
    raw_txns = fetch_open_banking_transactions(user_consents=consents)
    
    # 2. Xử lý gắn nhãn bằng AI/NLP qua danh mục hệ thống
    enriched_txns = process_all_transactions(raw_txns)
    
    # 3. Tính toán Sức khỏe tài chính, Dự báo dòng tiền, Hạn mức & Heo đất
    health_data = compute_financial_health(
        enriched_txns, 
        total_income=monthly_income,
        target_ratio=budget_ratio,
        category_budgets=category_budgets,
        round_up_config=round_up_config,
        savings_goals=savings_goals
    )
    
    banks = get_available_banks()
    
    return render_template(
        'dashboard.html',
        user=user,
        transactions=enriched_txns,
        health=health_data,
        banks=banks
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
# 6. BANK SYNC, CHATBOT & TRANSACTIONS
# ==========================================================================

@app.route('/api/sync-bank', methods=['POST'])
def api_sync_bank():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
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
def api_chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"reply": "Xin vui lòng nhập câu hỏi của bạn!"})
        
    user = get_current_user() or {}
    monthly_income = user.get('monthly_income', 18000000)
    budget_ratio = user.get('budget_ratio', {"needs": 50, "wants": 30, "savings": 20})
    savings_goals = user.get('savings_goals', [])
    round_up_config = user.get('round_up', {"enabled": True, "step": 10000, "accumulated_total": 0})
    category_budgets = user.get('category_limits', user.get('category_budgets', {}))
    consents = user.get('consents', [])
    
    raw_txns = fetch_open_banking_transactions(user_consents=consents)
    enriched_txns = process_all_transactions(raw_txns)
    health_data = compute_financial_health(
        enriched_txns, 
        total_income=monthly_income,
        target_ratio=budget_ratio,
        category_budgets=category_budgets,
        round_up_config=round_up_config,
        savings_goals=savings_goals
    )
    
    ai_reply = generate_chatbot_response(user_message, health_data)
    return jsonify({"reply": ai_reply})

@app.route('/api/transactions', methods=['GET'])
def api_transactions():
    user = get_current_user() or {}
    consents = user.get('consents', [])
    bank_filter = request.args.get('bank', 'ALL')
    
    raw_txns = fetch_open_banking_transactions(bank_filter, user_consents=consents)
    enriched = process_all_transactions(raw_txns)
    return jsonify({"total": len(enriched), "transactions": enriched})

# ==========================================================================
# 7. APP RUNNER
# ==========================================================================

if __name__ == '__main__':
    print("=================================================================")
    print("🚀 FINLAB ENTERPRISE PFM & ADMIN PORTAL ĐANG KHỞI CHẠY...")
    print("👉 Mở trình duyệt web và truy cập: http://127.0.0.1:5000")
    print("👉 Tài khoản User Demo: nguyen_van_a | Mật khẩu: password123")
    print("👉 Tài khoản Admin Demo: admin        | Mật khẩu: admin123")
    print("=================================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
