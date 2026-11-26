import json
import unicodedata
import uuid
from datetime import datetime
from functools import wraps

from flask import redirect, render_template, session, url_for
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from modules.database import (
    BankConsent,
    Category,
    CategoryBudget,
    SavingsGoal,
    SessionLocal,
    SystemSetting,
    User,
    Wallet,
)
from modules.health_scoring import suggest_ratio_by_income
from modules.open_banking import account_number_hmac, encrypt_access_token, encrypt_account_number
from modules.audit_logger import log_action


def _json_load(raw, fallback):
    if not raw:
        return fallback


def _password_fields(password):
    password_hash = generate_password_hash(str(password))
    parts = password_hash.split("$", 2)
    if len(parts) != 3:
        raise ValueError("Password hashing returned an unsupported format.")
    return password_hash, parts[1].encode("utf-8")
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


def _user_dict(db, row):
    consents = []
    for consent in row.bank_consents:
        scopes = _json_load(consent.scopes, []) or []
        consents.append({
            "consent_id": consent.consent_id,
            "bank_id": consent.provider_code,
            "provider_code": consent.provider_code,
            "bank_name": consent.provider_name,
            "provider_name": consent.provider_name,
            "scopes": scopes,
            "granted_at": consent.granted_at,
            "expires_at": consent.expires_at,
            "valid_until": consent.expires_at,
            "status": consent.status,
            "compliance": consent.compliance,
            "standard": consent.standard,
        })
    goals = [{
        "id": goal.id,
        "name": goal.goal_name,
        "goal_name": goal.goal_name,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "deadline": goal.deadline,
        "icon": goal.icon,
        "color": goal.color,
        "category": goal.category,
        "ai_forecast": goal.ai_forecast,
    } for goal in row.savings_goals]
    ratio = {
        "needs": row.needs_ratio,
        "wants": row.wants_ratio,
        "savings": row.savings_ratio,
    }
    budgets = {}
    for budget in row.category_budgets:
        if budget.category:
            budgets[budget.category.category_name] = budget.amount_limit
    round_up = {
        "enabled": bool(row.round_up_enabled),
        "step": row.round_up_step,
        "accumulated_total": row.round_up_accumulated,
        "goal_id": row.round_up_goal_id,
        "target_goal_id": row.round_up_goal_id,
    }
    wallets = [{
        "id": wallet.id,
        "name": wallet.wallet_name,
        "wallet_name": wallet.wallet_name,
        "type": wallet.wallet_type,
        "wallet_type": wallet.wallet_type,
        "provider_code": wallet.provider_code,
        "account_number": wallet.account_no_masked,
        "account_no_masked": wallet.account_no_masked,
        "initialBalance": wallet.initial_balance,
        "currentBalance": wallet.current_balance,
        "currency": wallet.currency,
        "connectionStatus": wallet.connection_status,
        "connection_status": wallet.connection_status,
        "consentId": wallet.consent_id,
        "note": wallet.note,
    } for wallet in row.wallets if wallet.connection_status != "ARCHIVED"]
    
    # Load custom transactions (MANUAL, OCR, PIS_SAVINGS) from Transaction table
    from modules.database import Transaction
    custom_txns = []
    # Get all wallet IDs for this user
    wallet_ids = [w.id for w in row.wallets]
    
    # Query transactions belonging to user's wallets OR without wallet (legacy/manual)
    if wallet_ids:
        transactions = db.query(Transaction).filter(
            or_(
                Transaction.wallet_id.in_(wallet_ids),
                Transaction.wallet_id.is_(None)
            ),
            Transaction.source.in_(["MANUAL", "OCR", "PIS_SAVINGS"])
        ).order_by(Transaction.timestamp.desc()).all()
    else:
        # User has no wallets, only get transactions without wallet
        transactions = db.query(Transaction).filter(
            Transaction.wallet_id.is_(None),
            Transaction.source.in_(["MANUAL", "OCR", "PIS_SAVINGS"])
        ).order_by(Transaction.timestamp.desc()).all()
    
    for txn in transactions:
        custom_txns.append({
            "id": txn.id,
            "timestamp": txn.timestamp,
            "bank": txn.wallet.wallet_name if txn.wallet else "Tiền mặt",
            "wallet_id": txn.wallet_id,
            "account_number": txn.wallet.account_no_masked if txn.wallet else "VÍ CÁ NHÂN",
            "type": txn.type,
            "amount": txn.amount,
            "description": txn.description,
            "category": txn.category.category_name if txn.category else None,
            "category_id": txn.category_id,
            "reference_code": txn.reference_code,
            "source": txn.source,
            "receipt_meta": _json_load(txn.receipt_meta_json, None)
        })
    
    return {
        "id": row.id,
        "username": row.username,
        "full_name": row.full_name,
        "email": row.email,
        "phone": row.phone or "",
        "role": row.role,
        "status": row.status,
        "created_at": row.created_at,
        "occupation": row.occupation or "Cá nhân",
        "monthly_income": row.monthly_income or 0,
        "budget_ratio": ratio,
        "goals": _json_load(row.onboarding_goals_json, []),
        "savings_goals": goals,
        "round_up": round_up,
        "round_up_enabled": bool(row.round_up_enabled),
        "category_limits": budgets,
        "category_budgets": budgets,
        "consents": consents,
        "connected_banks": [c["bank_name"] for c in consents if c["status"] == "ACTIVE"],
        "wallets": wallets,
        "custom_transactions": custom_txns,
        "open_banking_consent": {
            "view_balance": any("read_balance" in c["scopes"] for c in consents),
            "view_history": any("read_transactions" in c["scopes"] for c in consents),
            "ai_analytics": True,
        },
    }


def _get_row(db, user_id):
    return db.get(User, str(user_id))


def load_users():
    """Return user records in the legacy dictionary shape, backed by SQLite."""
    with SessionLocal() as db:
        return [_user_dict(db, row) for row in db.query(User).order_by(User.username).all()]


def save_users(users):
    """Compatibility import/update helper; application writes use targeted CRUD methods."""
    with SessionLocal() as db:
        try:
            for item in users:
                row = db.get(User, str(item.get("id", "")))
                if row is None:
                    continue
                _apply_user_updates(db, row, item)
            db.commit()
        except Exception:
            db.rollback()
            raise


def sanitize_user(user):
    """Normalize user data for frontend/session use without exposing credentials."""
    full_name = (user.get("full_name") or "").replace("(Verified)", "").strip()
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": full_name,
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": user.get("created_at", "2026-01-01"),
        "occupation": user.get("occupation", "Cá nhân"),
        "monthly_income": user.get("monthly_income", 18000000),
        "connected_banks": [c.get("bank_name") for c in user.get("consents", [])
                            if c.get("status") == "ACTIVE" and c.get("bank_name")]
                           or user.get("connected_banks", []),
        "goals": user.get("goals", []),
        "avatar_initial": full_name[0].upper() if full_name else "U",
        "budget_ratio": user.get("budget_ratio")
                        or suggest_ratio_by_income(user.get("monthly_income", 18000000)),
        "savings_goals": user.get("savings_goals", []),
        "round_up_enabled": user.get("round_up_enabled", True),
        "round_up": user.get("round_up", {"enabled": True, "step": 10000, "accumulated_total": 0}),
        "category_limits": user.get("category_limits", user.get("category_budgets", {})),
        "category_budgets": user.get("category_budgets", user.get("category_limits", {})),
        "open_banking_consent": user.get(
            "open_banking_consent",
            {"view_balance": True, "view_history": True, "ai_analytics": True},
        ),
        "consents": user.get("consents", []),
        "wallets": user.get("wallets", []),
        "custom_transactions": user.get("custom_transactions", []),
    }


def authenticate_user(username, password):
    if not username:
        return {"success": False, "message": "Vui lòng nhập Email, Số điện thoại hoặc Tên đăng nhập!"}
    ident = username.strip().lower()
    with SessionLocal() as db:
        row = db.query(User).filter(
            or_(
                User.username.ilike(ident),
                User.email.ilike(ident),
                User.phone == username.strip(),
            )
        ).first()
        if row is None:
            return {"success": False, "message": "Không tìm thấy tài khoản với thông tin đã nhập!"}
        if row.status.lower() == "locked":
            log_action(username, "Đăng nhập tài khoản bị khóa", row.id, "Failed",
                       "Người dùng thử đăng nhập nhưng tài khoản đang ở trạng thái locked")
            return {"success": False, "message": "Tài khoản của bạn đã bị khóa bởi Quản trị viên. Vui lòng liên hệ ban quản trị FinLab!"}
        if not password or not check_password_hash(row.password_hash, password):
            log_action(ident, "Đăng nhập sai mật khẩu", "FinLab App", "Failed",
                       "Nhập mật khẩu không chính xác")
            return {"success": False, "message": "Mật khẩu không chính xác. Vui lòng thử lại!"}
        user = sanitize_user(_user_dict(db, row))
        log_action(row.username, "Đăng nhập thành công", "FinLab App", "Success",
                   f"Đăng nhập qua định danh '{ident}'")
        return {"success": True, "user": user}


def _username_for(db, full_name):
    base = unicodedata.normalize("NFD", (full_name or "user").lower().replace(" ", "_"))
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    base = "".join(c for c in base if c.isalnum() or c == "_") or "user"
    candidate, counter = base, 1
    while db.query(User.id).filter(User.username == candidate).first():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def register_user(phone, full_name, email, password, goals=None, monthly_income=None, budget_ratio=None):
    with SessionLocal() as db:
        if phone and db.query(User.id).filter(User.phone == phone.strip()).first():
            return {"success": False, "message": "Số điện thoại này đã được đăng ký!"}
        if email and db.query(User.id).filter(User.email.ilike(email.strip())).first():
            return {"success": False, "message": "Email này đã được đăng ký!"}
        income = int(float(monthly_income)) if monthly_income else 18000000
        if income <= 0:
            income = 18000000
        suggested = suggest_ratio_by_income(income)
        ratio = budget_ratio if isinstance(budget_ratio, dict) else suggested
        values = [int(ratio.get(key, 0)) for key in ("needs", "wants", "savings")]
        if sum(values) != 100 or any(value < 0 or value > 100 for value in values):
            values = [suggested["needs"], suggested["wants"], suggested["savings"]]
        password_hash, password_salt = _password_fields(password)
        row = User(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            username=_username_for(db, full_name),
            password_hash=password_hash,
            password_salt=password_salt,
            full_name=full_name,
            email=email.strip().lower(),
            phone=phone.strip() if phone else None,
            role="user",
            status="active",
            created_at=datetime.now().isoformat(timespec="seconds"),
            occupation="Cá nhân",
            monthly_income=income,
            needs_ratio=values[0],
            wants_ratio=values[1],
            savings_ratio=values[2],
            onboarding_goals_json=json.dumps(goals or [], ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        return {"success": True, "user": sanitize_user(_user_dict(db, row))}


def user_exists_by_phone(phone):
    with SessionLocal() as db:
        return db.query(User.id).filter(User.phone == phone.strip()).first() is not None


def get_user_by_id(user_id):
    with SessionLocal() as db:
        row = _get_row(db, user_id)
        return _user_dict(db, row) if row else None


def get_all_users():
    return [sanitize_user(user) for user in load_users()]


def _sync_goals(db, row, items):
    items = items if isinstance(items, list) else []
    existing = {goal.id: goal for goal in row.savings_goals}
    seen = set()
    for item in items:
        goal_id = str(item.get("id") or item.get("goal_id") or f"goal_{uuid.uuid4().hex[:12]}")
        goal = existing.get(goal_id)
        if goal is None:
            goal = SavingsGoal(id=goal_id, user_id=row.id, goal_name="Mục tiêu")
            db.add(goal)
            row.savings_goals.append(goal)
        goal.user_id = row.id
        goal.goal_name = str(item.get("name") or item.get("goal_name") or "Mục tiêu")
        goal.target_amount = max(1, int(item.get("target_amount") or item.get("target") or 1))
        goal.current_amount = max(0, int(item.get("current_amount") or item.get("saved_amount") or 0))
        goal.deadline = str(item.get("deadline") or "2099-12-31")
        goal.icon = item.get("icon")
        goal.color = item.get("color")
        goal.category = item.get("category")
        goal.ai_forecast = item.get("ai_forecast")
        seen.add(goal_id)
    for goal_id, goal in existing.items():
        if goal_id not in seen:
            if row.round_up_goal_id == goal_id:
                row.round_up_goal_id = None
            row.savings_goals.remove(goal)


def _sync_consents(db, row, items):
    items = items if isinstance(items, list) else []
    existing = {consent.consent_id: consent for consent in row.bank_consents}
    seen = set()
    for item in items:
        consent_id = str(item.get("consent_id") or item.get("id") or "")
        if not consent_id:
            continue
        consent = existing.get(consent_id)
        if consent is None:
            consent = BankConsent(consent_id=consent_id, user_id=row.id)
            db.add(consent)
            row.bank_consents.append(consent)
        provider_code = str(item.get("bank_id") or item.get("provider_code") or "OTHER").upper()
        consent.provider_code = provider_code
        consent.provider_name = str(item.get("bank_name") or item.get("provider_name") or provider_code)
        scopes = item.get("scopes") or []
        if isinstance(scopes, dict):
            scopes = [key for key, enabled in scopes.items() if enabled]
        consent.scopes = json.dumps(scopes if isinstance(scopes, list) else [], ensure_ascii=False)
        consent.granted_at = str(item.get("granted_at") or datetime.now().date().isoformat())
        consent.expires_at = str(item.get("expires_at") or item.get("valid_until") or consent.granted_at)
        status = str(item.get("status") or "ACTIVE").upper()
        consent.status = status if status in ("ACTIVE", "REVOKED", "EXPIRED") else "ACTIVE"
        consent.compliance = item.get("compliance")
        consent.standard = item.get("standard")
        token = item.get("access_token") or item.get("token")
        if token:
            consent.encrypted_token = encrypt_access_token(token)
        seen.add(consent_id)
    for consent_id, consent in existing.items():
        if consent_id not in seen:
            consent.status = "REVOKED"


def _sync_wallets(db, row, items, consent_accounts=None):
    items = items if isinstance(items, list) else []
    consent_accounts = consent_accounts or {}
    existing = {wallet.id: wallet for wallet in row.wallets}
    consents = {consent.consent_id: consent for consent in row.bank_consents}
    seen = set()
    for item in items:
        wallet_id = str(item.get("id") or "")
        if not wallet_id:
            continue
        wallet = existing.get(wallet_id)
        if wallet is None:
            wallet = Wallet(id=wallet_id, user_id=row.id, wallet_name="Ví")
            db.add(wallet)
            row.wallets.append(wallet)
        wallet.user_id = row.id
        wallet.wallet_name = str(item.get("name") or item.get("wallet_name") or wallet.wallet_name)
        raw_type = str(item.get("type") or item.get("wallet_type") or "").upper()
        wallet.wallet_type = {
            "CASH": "CASH",
            "BANK": "BANK",
            "ACCOUNT": "BANK",
            "EWALLET": "E_WALLET",
            "E-WALLET": "E_WALLET",
            "E_WALLET": "E_WALLET",
            "WALLET": "E_WALLET",
        }.get(raw_type, "CASH")
        provider = str(item.get("provider_code") or item.get("bank_id") or item.get("provider") or "").upper()
        wallet.provider_code = provider or None
        consent_id = item.get("consentId") or item.get("consent_id")
        wallet.consent_id = str(consent_id) if consent_id and str(consent_id) in consents else None
        account_number = (
            item.get("account_number")
            or consent_accounts.get(str(consent_id))
            or (item.get("account_no") if not any(marker in str(item.get("account_no", "")) for marker in ("*", "•")) else None)
        )
        if account_number and not any(marker in str(account_number) for marker in ("*", "•")):
            wallet.account_no_encrypted = encrypt_account_number(account_number)
            wallet.account_no_masked = f"****{str(account_number)[-4:]}"
            if wallet.provider_code:
                wallet.account_no_hash = account_number_hmac(wallet.provider_code, account_number)
        else:
            masked = item.get("account_no_masked") or item.get("account_no")
            if masked and any(marker in str(masked) for marker in ("*", "•")):
                wallet.account_no_masked = str(masked)
        try:
            initial = item.get("initialBalance", item.get("initial_balance", wallet.initial_balance or 0))
            current = item.get("currentBalance", item.get("current_balance", wallet.current_balance or 0))
            wallet.initial_balance = max(0, int(float(initial or 0)))
            wallet.current_balance = max(0, int(float(current or 0)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid balance for wallet {wallet_id}.") from exc
        wallet.currency = str(item.get("currency") or "VND")
        status = str(item.get("connectionStatus") or item.get("connection_status") or "").upper()
        if status in ("MANUAL", "CONNECTED", "DISCONNECTED", "ERROR", "ARCHIVED"):
            wallet.connection_status = status
        elif wallet.consent_id:
            wallet.connection_status = "CONNECTED"
        else:
            wallet.connection_status = "MANUAL"
        wallet.note = item.get("note")
        wallet.created_at = str(item.get("createdAt") or item.get("created_at") or datetime.now().isoformat())
        wallet.updated_at = str(item.get("updatedAt") or item.get("updated_at") or wallet.created_at)
        wallet.last_synced_at = item.get("lastSyncedAt") or item.get("last_synced_at")
        seen.add(wallet_id)
    for wallet_id, wallet in existing.items():
        if wallet_id not in seen:
            wallet.connection_status = "ARCHIVED"


def _sync_transactions(db, row, items):
    from modules.database import Transaction, Category

    wallets = {wallet.id: wallet for wallet in row.wallets}
    by_name = {wallet.wallet_name.casefold(): wallet for wallet in row.wallets}
    
    # Tạo default wallet nếu user chưa có
    default_wallet = by_name.get("tiền mặt") or by_name.get("cash")
    if not default_wallet and not wallets:
        # Tạo wallet mặc định "Tiền mặt"
        from modules.database import Wallet
        import uuid
        from datetime import datetime
        default_wallet = Wallet(
            id=f"wallet_{uuid.uuid4().hex[:12]}",
            user_id=row.id,
            wallet_name="Tiền mặt",
            wallet_type="CASH",
            initial_balance=0,
            current_balance=0,
            currency="VND",
            connection_status="MANUAL",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        db.add(default_wallet)
        db.flush()  # Get the ID
        wallets[default_wallet.id] = default_wallet
        by_name["tiền mặt"] = default_wallet
    
    for item in items if isinstance(items, list) else []:
        txn_id = str(item.get("id") or "")
        if not txn_id:
            continue
        txn = db.get(Transaction, txn_id)
        if txn is None:
            txn = Transaction(id=txn_id, timestamp=str(item.get("timestamp") or datetime.now().isoformat()),
                              type=str(item.get("type") or "OUTFLOW").upper(),
                              amount=max(1, int(item.get("amount") or 1)), source="MANUAL")
            db.add(txn)
        bank = str(item.get("bank") or item.get("provider") or "").casefold()
        wallet = wallets.get(str(item.get("wallet_id") or "")) or by_name.get(bank)
        
        # Nếu không tìm thấy wallet, dùng default wallet
        if not wallet:
            wallet = default_wallet or list(wallets.values())[0] if wallets else None
        
        txn.wallet_id = wallet.id if wallet else None
        txn.timestamp = str(item.get("timestamp") or txn.timestamp)
        txn.type = str(item.get("type") or "OUTFLOW").upper()
        txn.amount = max(1, int(item.get("amount") or 1))
        txn.description = item.get("description")
        source = str(item.get("source") or "MANUAL").upper()
        txn.source = source if source in ("OPEN_BANKING", "MANUAL", "OCR", "PIS_SAVINGS") else "MANUAL"
        txn.reference_code = item.get("reference_code")
        txn.receipt_meta_json = json.dumps(item.get("receipt_meta"), ensure_ascii=False) if item.get("receipt_meta") else None
        
        # Map category name to category_id
        category_name = item.get("category")
        if category_name:
            category = db.query(Category).filter(Category.category_name == str(category_name)).first()
            if category:
                txn.category_id = category.id


def _sync_budgets(db, row, values):
    values = values if isinstance(values, dict) else {}
    existing = {b.category.category_name: b for b in row.category_budgets if b.category}
    start, end = datetime.now().date().replace(day=1), datetime.now().date()
    for name, amount in values.items():
        category = db.query(Category).filter(Category.category_name == str(name)).first()
        if category is None:
            continue
        budget = existing.get(str(name))
        if budget is None:
            budget = CategoryBudget(
                id=f"budget_{uuid.uuid4().hex[:12]}", user_id=row.id,
                category_id=category.id, period="MONTHLY",
                start_date=start.isoformat(), end_date=end.isoformat(),
            )
            db.add(budget)
        budget.amount_limit = max(0, int(amount))


def _apply_user_updates(db, row, updates):
    simple = {
        "username": "username", "full_name": "full_name", "email": "email",
        "phone": "phone", "role": "role", "status": "status",
        "occupation": "occupation", "monthly_income": "monthly_income",
    }
    for key, attr in simple.items():
        if key in updates:
            setattr(row, attr, updates[key])
    if "budget_ratio" in updates:
        ratio = updates["budget_ratio"] or {}
        row.needs_ratio = int(ratio.get("needs", row.needs_ratio))
        row.wants_ratio = int(ratio.get("wants", row.wants_ratio))
        row.savings_ratio = int(ratio.get("savings", row.savings_ratio))
    for key, column in (("goals", "onboarding_goals_json"),):
        if key in updates:
            setattr(row, column, json.dumps(updates[key] or [], ensure_ascii=False))
    if "savings_goals" in updates:
        _sync_goals(db, row, updates["savings_goals"])
    if "consents" in updates:
        _sync_consents(db, row, updates["consents"])
    if "wallets" in updates:
        consent_accounts = {
            str(item.get("consent_id") or item.get("id")): item.get("account_no")
            for item in updates.get("consents", [])
            if item.get("consent_id") or item.get("id")
        }
        _sync_wallets(db, row, updates["wallets"], consent_accounts)
    if "custom_transactions" in updates:
        _sync_transactions(db, row, updates["custom_transactions"])
    if "round_up_enabled" in updates:
        row.round_up_enabled = int(bool(updates["round_up_enabled"]))
    if "round_up" in updates:
        config = updates["round_up"] or {}
        row.round_up_enabled = int(bool(config.get("enabled", row.round_up_enabled)))
        row.round_up_step = max(1, int(config.get("step") or row.round_up_step))
        row.round_up_accumulated = max(0, int(config.get("accumulated_total") or 0))
        goal_id = config.get("goal_id") or config.get("goalId") or config.get("target_goal_id")
        if goal_id:
            goal = db.get(SavingsGoal, str(goal_id))
            if goal is None or goal.user_id != row.id:
                raise ValueError("Round-up goal must belong to the same user.")
            row.round_up_goal_id = goal.id
    if "category_budgets" in updates or "category_limits" in updates:
        _sync_budgets(db, row, updates.get("category_budgets", updates.get("category_limits")))


def update_user_field(user_id, field, value):
    return update_user(user_id, {field: value})


def update_user(user_id, updated_data):
    with SessionLocal() as db:
        try:
            row = _get_row(db, user_id)
            if row is None:
                return None
            _apply_user_updates(db, row, updated_data)
            db.commit()
            return sanitize_user(_user_dict(db, row))
        except Exception:
            db.rollback()
            raise


def toggle_user_status(user_id, admin_user=None):
    if admin_user and admin_user.get("id") == user_id:
        return None, "Bạn không thể tự khóa tài khoản của chính mình!"
    with SessionLocal() as db:
        row = _get_row(db, user_id)
        if row is None:
            return None, "Không tìm thấy người dùng!"
        old = row.status
        row.status = "locked" if old == "active" else "active"
        db.commit()
        action = "Khóa tài khoản" if row.status == "locked" else "Mở khóa tài khoản"
        log_action(admin_user.get("username") if admin_user else "admin", action,
                   f"{row.username} ({row.id})", details=f"Chuyển trạng thái từ '{old}' sang '{row.status}'")
        return row.status, f"Đã chuyển trạng thái tài khoản thành '{row.status}' thành công!"


def set_user_role(user_id, new_role, admin_user=None):
    if new_role not in ("admin", "user"):
        return False, "Vai trò không hợp lệ!"
    if admin_user and admin_user.get("id") == user_id and new_role != "admin":
        return False, "Bạn không thể tự hạ quyền Quản trị viên của chính mình!"
    with SessionLocal() as db:
        row = _get_row(db, user_id)
        if row is None:
            return False, "Không tìm thấy người dùng!"
        old_role = row.role
        row.role = new_role
        db.commit()
        log_action(admin_user.get("username") if admin_user else "admin", "Thay đổi vai trò",
                   f"{row.username} ({row.id})", details=f"Đổi quyền từ '{old_role}' sang '{new_role}'")
        return True, f"Đã cập nhật vai trò người dùng thành '{new_role}' thành công!"


def reset_user_password(user_id, new_password="password123", admin_user=None):
    with SessionLocal() as db:
        row = _get_row(db, user_id)
        if row is None:
            return False, "Không tìm thấy người dùng!"
        row.password_hash, row.password_salt = _password_fields(new_password)
        db.commit()
        log_action(admin_user.get("username") if admin_user else "admin", "Đặt lại mật khẩu",
                   f"{row.username} ({row.id})", details=f"Mật khẩu của {row.username} đã được đặt lại")
        return True, "Đặt lại mật khẩu thành công!"


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("user", {}).get("role") != "admin":
            return render_template(
                "login.html",
                error="Truy cập bị từ chối: Yêu cầu quyền Quản trị viên (Admin) để vào khu vực này!",
                username=session.get("user", {}).get("username"),
            ), 403
        return f(*args, **kwargs)
    return decorated_function
