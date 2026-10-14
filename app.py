import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from modules.auth import authenticate_user

from modules.open_banking import get_available_banks, fetch_open_banking_transactions, simulate_bank_connection
from modules.ai_categorizer import process_all_transactions
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response

app = Flask(__name__)
app.secret_key = "finlab_open_banking_ai_secret_key_2026"

# ==========================================================================
# 1. Authentication Routes
# ==========================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
        
    error = None
    username = ""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        auth_result = authenticate_user(username, password)
        if auth_result.get('success'):
            session['user'] = auth_result['user']
            return redirect(url_for('dashboard'))
        else:
            error = auth_result.get('message', 'Tên đăng nhập hoặc mật khẩu không đúng!')
            
    return render_template('login.html', error=error, username=username)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================================================
# 2. Main Dashboard Route
# ==========================================================================

@app.route('/')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user = session['user']
    monthly_income = user.get('monthly_income', 18000000)
    
    # 1. Đọc dữ liệu Open Banking
    raw_txns = fetch_open_banking_transactions()
    
    # 2. Xử lý gắn nhãn bằng AI/NLP
    enriched_txns = process_all_transactions(raw_txns)
    
    # 3. Tính toán Sức khỏe tài chính & Rò rỉ
    health_data = compute_financial_health(enriched_txns, total_income=monthly_income)
    
    # Danh sách ngân hàng khả dụng
    banks = get_available_banks()
    
    return render_template(
        'dashboard.html',
        user=user,
        transactions=enriched_txns,
        health=health_data,
        banks=banks
    )

# ==========================================================================
# 3. REST API Routes (Open Banking & AI Chatbot)
# ==========================================================================

@app.route('/api/sync-bank', methods=['POST'])
def api_sync_bank():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.get_json() or {}
    bank_id = data.get('bank_id', 'VCB')
    
    result = simulate_bank_connection(bank_id)
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"reply": "Xin vui lòng nhập câu hỏi của bạn!"})
        
    # Lấy thông tin tài chính người dùng hiện tại
    user = session.get('user', {})
    monthly_income = user.get('monthly_income', 18000000)
    
    raw_txns = fetch_open_banking_transactions()
    enriched_txns = process_all_transactions(raw_txns)
    health_data = compute_financial_health(enriched_txns, total_income=monthly_income)
    
    # AI sinh câu trả lời
    ai_reply = generate_chatbot_response(user_message, health_data)
    
    return jsonify({"reply": ai_reply})

@app.route('/api/transactions', methods=['GET'])
def api_transactions():
    bank_filter = request.args.get('bank', 'ALL')
    raw_txns = fetch_open_banking_transactions(bank_filter)
    enriched = process_all_transactions(raw_txns)
    return jsonify({"total": len(enriched), "transactions": enriched})

# ==========================================================================
# 4. App Runner
# ==========================================================================

if __name__ == '__main__':
    print("=================================================================")
    print("🚀 FINLAB WEB DEMO ĐANG KHỞI CHẠY...")
    print("👉 Mở trình duyệt web và truy cập: http://127.0.0.1:5000")
    print("👉 Tài khoản Demo: nguyen_van_a | Mật khẩu: password123")
    print("=================================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
