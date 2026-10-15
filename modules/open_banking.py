import json
import os
import time

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_transactions.json')

AVAILABLE_BANKS = [
    {
        "id": "VCB",
        "name": "Vietcombank",
        "short_name": "VCB",
        "account_no": "1028475938",
        "description": "STK: 1028475938 · Nhận lương",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Circular 64/2024/TT-NHNN)",
        "color": "#006837"
    },
    {
        "id": "TCB",
        "name": "Techcombank",
        "short_name": "TCB",
        "account_no": "19038475920",
        "description": "STK: 19038475920 · Chi tiêu hàng ngày",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Circular 64/2024/TT-NHNN)",
        "color": "#E31B23"
    },
    {
        "id": "MBB",
        "name": "MB Bank",
        "short_name": "MB",
        "account_no": "0987654321",
        "description": "STK: 0987654321 · Tiết kiệm số",
        "status": "CONNECTED",
        "api_standard": "Open API v2.1 (Circular 64/2024/TT-NHNN)",
        "color": "#002060"
    }
]

def get_available_banks():
    return AVAILABLE_BANKS

def fetch_open_banking_transactions(bank_filter=None):
    """
    Giả lập gọi Open Banking RESTful API (GET /api/v1/accounts/transactions)
    để đồng bộ lịch sử giao dịch từ các ngân hàng đối tác theo chuẩn OAuth 2.0.
    """
    if not os.path.exists(DATA_FILE):
        return []
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        transactions = json.load(f)
        
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
        
    return {
        "success": True,
        "bank": bank["name"],
        "account_no": bank["account_no"],
        "scope": "read:transactions read:balance",
        "consent_id": f"CONSENT_{bank_id}_{int(time.time())}",
        "message": f"Kết nối Open Banking API thành công với {bank['name']}!"
    }
