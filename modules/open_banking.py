import json
import os
import time
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_transactions.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

AVAILABLE_BANKS = [
    {
        "id": "VCB",
        "name": "Vietcombank",
        "short_name": "VCB",
        "account_no": "1028475938",
        "description": "STK: 1028475938 · Nhận lương",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#006837",
        "icon": "fa-building-columns"
    },
    {
        "id": "TCB",
        "name": "Techcombank",
        "short_name": "TCB",
        "account_no": "19038475920",
        "description": "STK: 19038475920 · Chi tiêu hàng ngày",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#E31B23",
        "icon": "fa-building-columns"
    },
    {
        "id": "MBB",
        "name": "MB Bank",
        "short_name": "MB",
        "account_no": "0987654321",
        "description": "STK: 0987654321 · Tiết kiệm số",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#002060",
        "icon": "fa-building-columns"
    }
]

def get_available_banks():
    return AVAILABLE_BANKS

def fetch_open_banking_transactions(bank_filter=None, user_consents=None):
    """
    Giả lập gọi Open Banking RESTful API (GET /api/v1/accounts/transactions)
    Có kiểm tra ủy quyền dữ liệu (Consent Check) tuân thủ Nghị định 13/2023/NĐ-CP.
    Nếu quyền 'read_transactions' bị thu hồi (Revoked), giao dịch từ ngân hàng đó sẽ tạm thời bị ngắt.
    """
    if not os.path.exists(DATA_FILE):
        return []
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            transactions = json.load(f)
        except Exception:
            return []

    # Kiểm tra Consent nếu có danh sách ủy quyền của người dùng
    if user_consents:
        # Lập danh sách các ngân hàng được phép đọc giao dịch
        allowed_bank_names = []
        for consent in user_consents:
            if consent.get("status") == "ACTIVE" and consent.get("scopes", {}).get("read_transactions", True):
                allowed_bank_names.append(consent.get("bank_name", "").lower())
                
        # Lọc giao dịch
        transactions = [
            t for t in transactions 
            if any(bname in t.get("bank", "").lower() for bname in allowed_bank_names)
        ]
        
    if bank_filter and bank_filter != 'ALL':
        transactions = [t for t in transactions if t.get('bank', '').lower() == bank_filter.lower()]
        
    return transactions

def simulate_bank_connection(bank_id):
    """
    Giả lập quy trình người dùng cấp quyền ủy quyền OAuth 2.0 (Consent)
    cho FinLab đọc dữ liệu tài khoản (AIS).
    """
    bank = next((b for b in AVAILABLE_BANKS if b['id'] == bank_id), None)
    if not bank:
        return {"success": False, "message": "Ngân hàng không hợp lệ"}
        
    now = datetime.now()
    expiry = now + timedelta(days=90) # Chuẩn 90 ngày của Open Banking Consent
    
    return {
        "success": True,
        "bank": bank["name"],
        "bank_id": bank["id"],
        "account_no": bank["account_no"],
        "scope": "read:transactions read:balance analyze:ai_pfm",
        "consent_id": f"CONSENT_{bank_id}_{int(time.time())}",
        "granted_at": now.strftime("%Y-%m-%d"),
        "expires_at": expiry.strftime("%Y-%m-%d"),
        "message": f"Kết nối Open Banking API thành công với {bank['name']}!"
    }
