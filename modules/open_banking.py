import json
import os
import time
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_transactions.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

# Danh mục các tổ chức tín dụng & trung gian thanh toán hỗ trợ Open Banking API
AVAILABLE_PROVIDERS = [
    {
        "id": "VCB",
        "name": "Vietcombank",
        "short_name": "VCB",
        "type": "bank",
        "account_no": "1028475938",
        "account_type": "Tài khoản thanh toán (VND)",
        "default_balance": 18200000,
        "description": "STK: 1028475938 · Nhận lương & Chi tiêu",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#006837",
        "gradient": "linear-gradient(135deg, #0A4D2E 0%, #006837 60%, #15803D 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://digibank.vietcombank.com.vn/open-api/oauth/authorize"
    },
    {
        "id": "TCB",
        "name": "Techcombank",
        "short_name": "TCB",
        "type": "bank",
        "account_no": "19038475920",
        "account_type": "Tài khoản thanh toán (VND)",
        "default_balance": 28500000,
        "description": "STK: 19038475920 · Chi tiêu hàng ngày & Quẹt thẻ",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#E31B23",
        "gradient": "linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 50%, #E8632A 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://techcombank.com.vn/open-banking/oauth"
    },
    {
        "id": "MBB",
        "name": "MB Bank",
        "short_name": "MB",
        "type": "bank",
        "account_no": "0987654321",
        "account_type": "Tài khoản số đẹp (VND)",
        "default_balance": 7500000,
        "description": "STK: 0987654321 · Tiết kiệm số & Đầu tư",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#002060",
        "gradient": "linear-gradient(135deg, #0B1D4F 0%, #002060 60%, #1D4ED8 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://mbbank.com.vn/oauth/v2"
    },
    {
        "id": "CTG",
        "name": "VietinBank",
        "short_name": "Vietin",
        "type": "bank",
        "account_no": "10982736451",
        "account_type": "Tài khoản iPay (VND)",
        "default_balance": 12000000,
        "description": "STK: 10982736451 · Tài khoản iPay",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#00558F",
        "gradient": "linear-gradient(135deg, #003366 0%, #00558F 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://vietinbank.vn/open-api"
    },
    {
        "id": "BIDV",
        "name": "BIDV",
        "short_name": "BIDV",
        "type": "bank",
        "account_no": "1209876543",
        "account_type": "SmartBanking (VND)",
        "default_balance": 9800000,
        "description": "STK: 1209876543 · BIDV SmartBanking",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#007A3D",
        "gradient": "linear-gradient(135deg, #004D25 0%, #007A3D 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://smartbanking.bidv.com.vn"
    },
    {
        "id": "ACB",
        "name": "ACB",
        "short_name": "ACB",
        "type": "bank",
        "account_no": "246813579",
        "account_type": "ACB ONE (VND)",
        "default_balance": 15400000,
        "description": "STK: 246813579 · ACB ONE Digital",
        "api_standard": "Open API v2.1 (Thông tư 64/2024/TT-NHNN)",
        "color": "#005BAA",
        "gradient": "linear-gradient(135deg, #003F7A 0%, #005BAA 100%)",
        "icon": "fa-building-columns",
        "auth_url_mock": "https://acb.com.vn/oauth"
    },
    {
        "id": "MOMO",
        "name": "MoMo",
        "short_name": "MoMo",
        "type": "ewallet",
        "account_no": "0912345678",
        "account_type": "Ví điện tử MoMo",
        "default_balance": 3150000,
        "description": "Ví SĐT: 0912345678 · Thanh toán hóa đơn & Ăn uống",
        "api_standard": "Open API AIS v1.0",
        "color": "#A50064",
        "gradient": "linear-gradient(135deg, #A50064 0%, #C4167E 60%, #E8632A 100%)",
        "icon": "fa-mobile-screen-button",
        "auth_url_mock": "https://momo.vn/open-api/oauth"
    },
    {
        "id": "ZALOPAY",
        "name": "ZaloPay",
        "short_name": "ZaloPay",
        "type": "ewallet",
        "account_no": "0987654321",
        "account_type": "Ví điện tử ZaloPay",
        "default_balance": 1850000,
        "description": "Ví SĐT: 0987654321 · Chuyển tiền & Mua sắm",
        "api_standard": "Open API AIS v1.0",
        "color": "#0068FF",
        "gradient": "linear-gradient(135deg, #004ecc 0%, #0068FF 100%)",
        "icon": "fa-mobile-screen-button",
        "auth_url_mock": "https://zalopay.vn/oauth"
    },
    {
        "id": "SHOPEEPAY",
        "name": "ShopeePay",
        "short_name": "ShopeePay",
        "type": "ewallet",
        "account_no": "0934567890",
        "account_type": "Ví điện tử ShopeePay",
        "default_balance": 920000,
        "description": "Ví ShopeePay · Săn sale & Giao đồ ăn",
        "api_standard": "Open API AIS v1.0",
        "color": "#EE4D2D",
        "gradient": "linear-gradient(135deg, #C23518 0%, #EE4D2D 100%)",
        "icon": "fa-bag-shopping",
        "auth_url_mock": "https://shopeepay.vn/oauth"
    }
]

# Backward compatibility alias
AVAILABLE_BANKS = AVAILABLE_PROVIDERS

def get_available_banks(user_consents=None):
    """
    Trả về danh sách các ngân hàng & ví điện tử,
    tự động đối chiếu với danh sách ủy quyền (consents) của người dùng để trả về trạng thái CONNECTED / NOT_CONNECTED.
    """
    consents_map = {}
    if user_consents:
        for c in user_consents:
            bank_id = (c.get("bank_id") or "").upper()
            consents_map[bank_id] = c

    result = []
    for p in AVAILABLE_PROVIDERS:
        item = dict(p)
        c = consents_map.get(item["id"].upper())
        if c and c.get("status") == "ACTIVE":
            item["status"] = "CONNECTED"
            item["connected"] = True
            item["consent_id"] = c.get("consent_id")
            item["granted_at"] = c.get("granted_at")
            item["expires_at"] = c.get("expires_at")
            item["scopes"] = c.get("scopes", {})
        elif c and c.get("status") == "REVOKED":
            item["status"] = "REVOKED"
            item["connected"] = False
            item["consent_id"] = c.get("consent_id")
            item["scopes"] = c.get("scopes", {})
        else:
            item["status"] = "NOT_CONNECTED"
            item["connected"] = False
        result.append(item)
    return result

def get_provider_by_id(provider_id):
    if not provider_id:
        return None
    pid = provider_id.upper().strip()
    for p in AVAILABLE_PROVIDERS:
        if p["id"].upper() == pid or p["short_name"].upper() == pid:
            return p
    return None

def fetch_open_banking_transactions(bank_filter=None, user_consents=None):
    """
    Giả lập gọi Open Banking RESTful API (GET /api/v1/accounts/transactions)
    Có kiểm tra ủy quyền dữ liệu (Consent Check) tuân thủ Nghị định 13/2023/NĐ-CP.
    Nếu quyền 'read_transactions' bị thu hồi (Revoked) hoặc ngân hàng chưa được cấp phép,
    giao dịch từ ngân hàng đó sẽ bị lọc bỏ.
    """
    if not os.path.exists(DATA_FILE):
        return []
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            transactions = json.load(f)
        except Exception:
            return []

    # Kiểm tra Consent nếu danh sách ủy quyền được truyền vào
    if user_consents is not None:
        allowed_bank_keywords = []
        for consent in user_consents:
            scopes = consent.get("scopes", {})
            if isinstance(scopes, list):
                has_tx_scope = "read_transactions" in scopes
            elif isinstance(scopes, dict):
                has_tx_scope = bool(scopes.get("read_transactions", True))
            else:
                has_tx_scope = True

            if consent.get("status") == "ACTIVE" and has_tx_scope:
                b_name = consent.get("bank_name", "").lower()
                b_id = consent.get("bank_id", "").lower()
                if b_name:
                    allowed_bank_keywords.append(b_name)
                if b_id:
                    allowed_bank_keywords.append(b_id)
                # Map short names
                p = get_provider_by_id(b_id)
                if p:
                    allowed_bank_keywords.append(p["name"].lower())
                    allowed_bank_keywords.append(p["short_name"].lower())

        # Nếu người dùng không có ngân hàng nào được cấp quyền xem giao dịch -> Trả về rỗng
        if not allowed_bank_keywords:
            return []

        # Lọc giao dịch chỉ thuộc các ngân hàng đã được ủy quyền
        transactions = [
            t for t in transactions 
            if any(kw in t.get("bank", "").lower() for kw in allowed_bank_keywords)
        ]
        
    if bank_filter and bank_filter != 'ALL':
        transactions = [t for t in transactions if bank_filter.lower() in t.get('bank', '').lower()]
        
    return transactions

def simulate_bank_connection(bank_id, account_no=None, custom_balance=None, scopes=None, consent_confirmed=True):
    """
    Giả lập quy trình người dùng hoàn tất OAuth 2.0 & xác nhận Consent
    để liên kết tài khoản ngân hàng hoặc ví điện tử theo chuẩn Open Banking API.
    """
    provider = get_provider_by_id(bank_id)
    if not provider:
        return {"success": False, "message": f"Nhà cung cấp '{bank_id}' không hợp lệ hoặc chưa được hỗ trợ."}
        
    if not consent_confirmed:
        return {
            "success": False,
            "message": "Bạn cần đánh dấu đồng ý cam kết chia sẻ dữ liệu theo Nghị định 13/2023/NĐ-CP để tiếp tục."
        }

    now = datetime.now()
    expiry = now + timedelta(days=90)  # Chuẩn 90 ngày của Open Banking Consent (AIS)

    selected_account = account_no or provider["account_no"]
    balance = custom_balance if (custom_balance is not None and custom_balance >= 0) else provider["default_balance"]

    default_scopes = {
        "read_balance": True,
        "read_transactions": True,
        "analyze_ai": True
    }
    if isinstance(scopes, dict):
        default_scopes.update(scopes)

    consent_id = f"CONSENT_{provider['id']}_{int(time.time())}"

    consent_obj = {
        "consent_id": consent_id,
        "bank_id": provider["id"],
        "bank_name": provider["name"],
        "account_no": selected_account,
        "status": "ACTIVE",
        "granted_at": now.strftime("%Y-%m-%d"),
        "expires_at": expiry.strftime("%Y-%m-%d"),
        "scopes": default_scopes,
        "compliance": "Nghị định 13/2023/NĐ-CP & Thông tư 64/2024/TT-NHNN",
        "standard": provider["api_standard"]
    }

    # Tạo đối tượng ví liên kết tương ứng
    wallet_obj = {
        "id": f"W_OB_{provider['id']}_{int(time.time())}",
        "name": f"{provider['name']} · {selected_account[-4:] if len(selected_account) >= 4 else selected_account}",
        "type": provider["type"],
        "provider": provider["name"],
        "account_no": f"•••• {selected_account[-4:] if len(selected_account) >= 4 else selected_account}",
        "initialBalance": balance,
        "currentBalance": balance,
        "managementMode": "connect",
        "connectionStatus": "connected",
        "consentId": consent_id,
        "note": f"Liên kết Open Banking ({provider['api_standard']})",
        "color": provider.get("gradient", provider.get("color")),
        "createdAt": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "lastSyncedAt": now.strftime("%Y-%m-%d %H:%M")
    }

    return {
        "success": True,
        "message": f"Kết nối Open Banking API thành công với {provider['name']}!",
        "consent": consent_obj,
        "wallet": wallet_obj,
        "provider": provider
    }
