import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from modules.auth import authenticate_user, register_user, user_exists_by_phone
from modules.open_banking import get_available_banks, fetch_open_banking_transactions, simulate_bank_connection
from modules.ai_categorizer import process_all_transactions
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response

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
    enriched_txns = process_all_transactions(raw_txns)
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
    phone = ''
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if not phone or len(phone) < 9:
            error = 'Vui lòng nhập số điện thoại hợp lệ!'
        else:
            session['reg_phone'] = phone
            return redirect(url_for('register_otp'))
    return render_template('register.html', error=error, phone=phone)

@app.route('/register/otp', methods=['GET', 'POST'])
def register_otp():
    if 'reg_phone' not in session:
        return redirect(url_for('register'))
    error = None
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if len(otp) == 6 and otp.isdigit():
            session['reg_otp_verified'] = True
            return redirect(url_for('register_create'))
        else:
            error = 'Mã OTP không hợp lệ. Vui lòng nhập đủ 6 chữ số!'
    phone = session.get('reg_phone', '')
    return render_template('register_otp.html', phone=phone, error=error)

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
