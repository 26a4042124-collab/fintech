import os
import sys
import time

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

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from modules.auth import authenticate_user, register_user, user_exists_by_phone
from modules.open_banking import get_available_banks, fetch_open_banking_transactions, simulate_bank_connection
from modules.ai_categorizer import process_all_transactions
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response
from modules.otp_service import generate_otp, send_otp_email, verify_otp

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'finlab_canva_redesign_secret_2026')

# ==========================================================================
# Helpers
# ==========================================================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated

def get_financial_data():
    user = session.get('user', {})
    monthly_income = user.get('monthly_income', 18000000)
    raw_txns = fetch_open_banking_transactions()
    custom_txns = session.get('custom_transactions', [])
    all_txns = list(custom_txns) + list(raw_txns)
    enriched_txns = process_all_transactions(all_txns)
    health_data = compute_financial_health(enriched_txns, total_income=monthly_income)
    return enriched_txns, health_data

# ==========================================================================
# 1. Landing / Onboarding
# ==========================================================================
@app.route('/')
def landing():
    if 'user' in session:
        return redirect(url_for('dashboard'))
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
    if 'user' in session:
        return redirect(url_for('dashboard'))
    error = None
    username = ''
    register_success = session.pop('register_success', False)
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        auth_result = authenticate_user(username, password)
        if auth_result.get('success'):
            session['user'] = auth_result['user']
            return redirect(url_for('dashboard'))
        else:
            error = auth_result.get('message', 'Thông tin đăng nhập không chính xác!')
    return render_template('login.html', error=error, username=username, register_success=register_success)

@app.route('/logout')
def logout():
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
    # Tính balance (income - expense)
    balance = health_data.get('income', 0) - health_data.get('total_expense', 0)
    return render_template('dashboard.html',
        user=user,
        transactions=enriched_txns[:5],
        health=health_data,
        banks=banks,
        balance=balance
    )

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
    budgets_list = [
        {
            "category": "Ăn uống & Cà phê",
            "icon": "utensils",
            "spent": 4200000,
            "limit": 5500000,
            "color": "#E8632A",
            "bg": "rgba(232, 99, 42, 0.12)"
        },
        {
            "category": "Đi lại & Xăng xe",
            "icon": "motorcycle",
            "spent": 950000,
            "limit": 1500000,
            "color": "#3B82F6",
            "bg": "rgba(59, 130, 246, 0.12)"
        },
        {
            "category": "Mua sắm cá nhân",
            "icon": "bag-shopping",
            "spent": 3100000,
            "limit": 3000000,
            "color": "#EF4444",
            "bg": "rgba(239, 68, 68, 0.12)"
        },
        {
            "category": "Nhà cửa & Hóa đơn",
            "icon": "house",
            "spent": 3500000,
            "limit": 4000000,
            "color": "#10B981",
            "bg": "rgba(16, 185, 129, 0.12)"
        },
        {
            "category": "Giải trí & Bạn bè",
            "icon": "film",
            "spent": 1200000,
            "limit": 2000000,
            "color": "#8B5CF6",
            "bg": "rgba(139, 92, 246, 0.12)"
        },
        {
            "category": "Sức khỏe & Thuốc",
            "icon": "heart-pulse",
            "spent": 350000,
            "limit": 1000000,
            "color": "#06B6D4",
            "bg": "rgba(6, 182, 212, 0.12)"
        }
    ]
    
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
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"reply": "Xin vui lòng nhập câu hỏi của bạn!"})
    user = session.get('user', {})
    monthly_income = user.get('monthly_income', 18000000)
    raw_txns = fetch_open_banking_transactions()
    enriched_txns = process_all_transactions(raw_txns)
    health_data = compute_financial_health(enriched_txns, total_income=monthly_income)
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
# 10. App Runner
# ==========================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 FINLAB (Canva Redesign) ĐANG KHỞI CHẠY...")
    print(f"👉 Truy cập: http://127.0.0.1:{port}")
    print("👉 Demo: nguyen_van_a | password123")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=True)
