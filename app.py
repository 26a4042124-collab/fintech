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
    balance = health_data.get('income', 0) - health_data.get('total_expense', 0)
    
    wallets_data = [
        {
            "id": "tcb",
            "name": "Techcombank Visa",
            "type": "Tài khoản thanh toán",
            "account_no": "1903 •••• 5920",
            "balance": 28500000,
            "color": "linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 50%, #E8632A 100%)",
            "text_color": "#FFFFFF",
            "brand": "TECHCOMBANK",
            "icon": "fa-credit-card",
            "status": "Đang hoạt động"
        },
        {
            "id": "vcb",
            "name": "Vietcombank Connect24",
            "type": "Tài khoản nhận lương",
            "account_no": "1028 •••• 5938",
            "balance": 18200000,
            "color": "linear-gradient(135deg, #0A4D2E 0%, #006837 60%, #15803D 100%)",
            "text_color": "#FFFFFF",
            "brand": "VIETCOMBANK",
            "icon": "fa-building-columns",
            "status": "Đang hoạt động"
        },
        {
            "id": "mbb",
            "name": "MB Bank Số đẹp",
            "type": "Tài khoản tiết kiệm",
            "account_no": "0987 •••• 4321",
            "balance": 7500000,
            "color": "linear-gradient(135deg, #0B1D4F 0%, #002060 60%, #1D4ED8 100%)",
            "text_color": "#FFFFFF",
            "brand": "MB BANK",
            "icon": "fa-piggy-bank",
            "status": "Đang hoạt động"
        },
        {
            "id": "momo",
            "name": "Ví điện tử MoMo",
            "type": "Ví thanh toán di động",
            "account_no": "0912 •••• 789",
            "balance": 3150000,
            "color": "linear-gradient(135deg, #A50064 0%, #C4167E 60%, #E8632A 100%)",
            "text_color": "#FFFFFF",
            "brand": "MOMO PAY",
            "icon": "fa-wallet",
            "status": "Đang hoạt động"
        },
        {
            "id": "cash",
            "name": "Tiền mặt trong ví",
            "type": "Tiền mặt",
            "account_no": "Ví cá nhân",
            "balance": 2000000,
            "color": "linear-gradient(135deg, #2D3748 0%, #4A5568 100%)",
            "text_color": "#FFFFFF",
            "brand": "TIỀN MẶT",
            "icon": "fa-money-bill-wave",
            "status": "Sẵn sàng"
        }
    ]
    total_assets = sum(w['balance'] for w in wallets_data)

    return render_template('wallets.html',
        user=session['user'],
        wallets=wallets_data,
        total_assets=total_assets,
        balance=balance,
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
