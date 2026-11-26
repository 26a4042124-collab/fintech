import json
import os
from calendar import monthrange
from datetime import date, datetime

from dotenv import load_dotenv
from sqlalchemy import case, func

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from modules.database import (
    AuditLog,
    BankConsent,
    Category,
    CategoryBudget,
    CreditAccount,
    SavingsGoal,
    SessionLocal,
    SystemSetting,
    Transaction,
    User,
    Wallet,
    init_db,
    session_scope,
)
from modules.open_banking import account_number_hmac, encrypt_access_token, encrypt_account_number
from werkzeug.security import generate_password_hash


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASELINE_USERNAME = "nguyen_van_a"
EXPECTED_BASELINE = {
    "transactions": 35,
    "net_balance": 4_451_000,
    "final_balance": 22_451_000,  # initial 18M + net 4.451M
    "monthly_income": 18_000_000,
}

PROVIDERS = {
    "VCB": "Vietcombank",
    "TCB": "Techcombank",
    "MBB": "MB Bank",
    "MB": "MB Bank",
    "CTG": "VietinBank",
    "BIDV": "BIDV",
    "ACB": "ACB",
    "MOMO": "MoMo",
    "ZALOPAY": "ZaloPay",
    "SHOPEEPAY": "ShopeePay",
}

PROVIDER_ALIASES = {
    "vietcombank": "VCB",
    "vcb": "VCB",
    "techcombank": "TCB",
    "tcb": "TCB",
    "mb bank": "MBB",
    "mbbank": "MBB",
    "mb": "MBB",
    "vietinbank": "CTG",
    "vietin": "CTG",
    "bidv": "BIDV",
    "acb": "ACB",
    "momo": "MOMO",
    "zalopay": "ZALOPAY",
    "shopeepay": "SHOPEEPAY",
}


def _read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as source:
        return json.load(source)


def _dump_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _password_fields(raw_password):
    password_hash = generate_password_hash(str(raw_password))
    try:
        embedded_salt = password_hash.split("$", 2)[1]
    except IndexError as exc:
        raise ValueError("Werkzeug returned an unsupported password hash format.") from exc
    return password_hash, embedded_salt.encode("utf-8")


def _ratio_fields(user_data):
    ratio = user_data.get("budget_ratio") or {}
    values = (
        int(ratio.get("needs", 50)),
        int(ratio.get("wants", 30)),
        int(ratio.get("savings", 20)),
    )
    if sum(values) != 100 or any(value < 0 or value > 100 for value in values):
        return 50, 30, 20
    return values


def _provider_code(value):
    normalized = str(value or "").strip().lower()
    if normalized in PROVIDER_ALIASES:
        return PROVIDER_ALIASES[normalized]
    upper = str(value or "").strip().upper()
    return upper if upper in PROVIDERS else "OTHER"


def _wallet_type(wallet_data, provider_code):
    raw_type = str(wallet_data.get("type") or wallet_data.get("wallet_type") or "").lower()
    if raw_type in ("bank", "credit", "account"):
        return "BANK"
    if raw_type in ("ewallet", "e_wallet", "wallet"):
        return "E_WALLET"
    if provider_code in ("MOMO", "ZALOPAY", "SHOPEEPAY"):
        return "E_WALLET"
    return "CASH"


def _wallet_status(wallet_data, has_consent):
    raw_status = str(
        wallet_data.get("connectionStatus")
        or wallet_data.get("connection_status")
        or ""
    ).upper()
    if raw_status == "ARCHIVED":
        return "ARCHIVED"
    if raw_status in ("CONNECTED", "DISCONNECTED", "ERROR"):
        return raw_status
    return "CONNECTED" if has_consent else "MANUAL"


def _date_range_for_month():
    today = date.today()
    first = today.replace(day=1)
    last = today.replace(day=monthrange(today.year, today.month)[1])
    return first.isoformat(), last.isoformat()


def _system_setting_value(value):
    if isinstance(value, bool):
        return "BOOL", "true" if value else "false"
    if isinstance(value, int):
        return "INT", str(value)
    if isinstance(value, (dict, list)):
        return "JSON", _dump_json(value)
    return "STRING", str(value)


def _upsert_user(session, user_data):
    user_id = str(user_data.get("id") or "")
    if not user_id:
        raise ValueError("A user record is missing its id.")
    ratio = _ratio_fields(user_data)
    user = session.get(User, user_id)
    raw_password = user_data.get("password")
    stored_hash = user_data.get("password_hash")
    if user is None:
        if not stored_hash:
            if raw_password is None:
                raise ValueError(f"User {user_id} has no password to hash.")
            stored_hash, salt = _password_fields(raw_password)
        else:
            salt = str(user_data.get("password_salt") or "imported").encode("utf-8")
        user = User(
            id=user_id,
            username=str(user_data.get("username") or user_id),
            password_hash=stored_hash,
            password_salt=salt,
            full_name=str(user_data.get("full_name") or user_data.get("username") or user_id),
            email=str(user_data.get("email") or f"{user_id}@invalid.local"),
            phone=user_data.get("phone") or None,
            role=str(user_data.get("role") or "user").lower(),
            status=str(user_data.get("status") or "active").lower(),
            created_at=str(user_data.get("created_at") or datetime.now().isoformat()),
            occupation=user_data.get("occupation"),
            monthly_income=int(user_data["monthly_income"]) if user_data.get("monthly_income") is not None else None,
            needs_ratio=ratio[0],
            wants_ratio=ratio[1],
            savings_ratio=ratio[2],
            onboarding_goals_json=_dump_json(user_data.get("goals") or []),
            round_up_enabled=int(bool(user_data.get("round_up_enabled", True))),
        )
        session.add(user)
    else:
        user.username = str(user_data.get("username") or user.username)
        user.full_name = str(user_data.get("full_name") or user.full_name)
        user.email = str(user_data.get("email") or user.email)
        user.phone = user_data.get("phone") or None
        user.role = str(user_data.get("role") or "user").lower()
        user.status = str(user_data.get("status") or "active").lower()
        user.occupation = user_data.get("occupation")
        if user_data.get("monthly_income") is not None:
            user.monthly_income = int(user_data["monthly_income"])
        user.needs_ratio, user.wants_ratio, user.savings_ratio = ratio
        user.onboarding_goals_json = _dump_json(user_data.get("goals") or [])
    if stored_hash:
        user.password_hash = stored_hash
        user.password_salt = str(user_data.get("password_salt") or "imported").encode("utf-8")
    elif raw_password is not None and not user.password_hash:
        user.password_hash, user.password_salt = _password_fields(raw_password)

    round_up = user_data.get("round_up") or {}
    user.round_up_enabled = int(bool(round_up.get("enabled", user_data.get("round_up_enabled", True))))
    user.round_up_step = max(1, int(round_up.get("step") or 1000))
    user.round_up_accumulated = max(0, int(round_up.get("accumulated_total") or 0))
    return user


def _upsert_consent(session, user, consent_data):
    consent_id = str(consent_data.get("consent_id") or "")
    if not consent_id:
        return None
    provider_code = _provider_code(consent_data.get("bank_id") or consent_data.get("provider_code"))
    provider_name = str(
        consent_data.get("bank_name")
        or consent_data.get("provider_name")
        or PROVIDERS.get(provider_code, provider_code)
    )
    scopes = consent_data.get("scopes") or []
    if isinstance(scopes, dict):
        scopes = [scope for scope, enabled in scopes.items() if enabled]
    if not isinstance(scopes, list):
        scopes = []
    row = session.get(BankConsent, consent_id)
    if row is None:
        row = BankConsent(consent_id=consent_id, user_id=user.id)
        session.add(row)
    row.user_id = user.id
    row.provider_code = provider_code
    row.provider_name = provider_name
    row.scopes = _dump_json(scopes)
    row.granted_at = str(consent_data.get("granted_at") or datetime.now().date().isoformat())
    row.expires_at = str(consent_data.get("expires_at") or consent_data.get("valid_until") or row.granted_at)
    status = str(consent_data.get("status") or "ACTIVE").upper()
    row.status = status if status in ("ACTIVE", "REVOKED", "EXPIRED") else "ACTIVE"
    row.compliance = consent_data.get("compliance")
    row.standard = consent_data.get("standard")
    token = consent_data.get("access_token") or consent_data.get("token")
    if token:
        row.encrypted_token = encrypt_access_token(token)
    return row


def _build_wallet(session, user, wallet_data, consents_by_id, consents_by_provider):
    wallet_id = str(wallet_data.get("id") or "")
    if not wallet_id:
        raise ValueError(f"A wallet for user {user.id} is missing its id.")
    consent_id = wallet_data.get("consentId") or wallet_data.get("consent_id")
    consent = consents_by_id.get(str(consent_id)) if consent_id else None
    provider_code = _provider_code(
        wallet_data.get("bank_id")
        or wallet_data.get("provider_code")
        or (consent.provider_code if consent else wallet_data.get("provider"))
    )
    if consent is None and provider_code in consents_by_provider:
        consent = consents_by_provider[provider_code]
        consent_id = consent.consent_id

    account_number = wallet_data.get("account_number") or wallet_data.get("account_no")
    consent_payload = wallet_data.get("_consent_payload") or {}
    if consent_payload.get("account_no"):
        account_number = consent_payload["account_no"]
    if account_number and any(marker in str(account_number) for marker in ("•", "*")):
        account_number = None

    row = session.get(Wallet, wallet_id)
    if row is None:
        row = Wallet(id=wallet_id, user_id=user.id, wallet_name=str(wallet_data.get("name") or wallet_data.get("wallet_name") or "Ví"))
        session.add(row)
    row.user_id = user.id
    row.consent_id = consent.consent_id if consent else None
    row.wallet_name = str(wallet_data.get("name") or wallet_data.get("wallet_name") or "Ví")
    row.provider_code = provider_code if provider_code != "OTHER" else None
    row.wallet_type = _wallet_type(wallet_data, provider_code)
    initial = max(0, int(float(wallet_data.get("initialBalance", wallet_data.get("initial_balance", 0)) or 0)))
    row.initial_balance = initial
    # Set current_balance to initial_balance; transactions will update it later
    row.current_balance = initial
    row.currency = str(wallet_data.get("currency") or "VND")
    row.connection_status = _wallet_status(wallet_data, consent is not None)
    row.note = wallet_data.get("note")
    row.created_at = str(wallet_data.get("createdAt") or wallet_data.get("created_at") or datetime.now().isoformat())
    row.updated_at = str(wallet_data.get("updatedAt") or wallet_data.get("updated_at") or row.created_at)
    row.last_synced_at = wallet_data.get("lastSyncedAt") or wallet_data.get("last_synced_at")
    if account_number and row.provider_code:
        row.account_no_encrypted = encrypt_account_number(account_number)
        row.account_no_hash = account_number_hmac(row.provider_code, account_number)
        row.account_no_masked = str(wallet_data.get("account_no_masked") or f"****{str(account_number)[-4:]}")
    elif wallet_data.get("account_no_masked"):
        row.account_no_masked = wallet_data["account_no_masked"]
    return row


def _upsert_goal(session, user, goal_data):
    goal_id = str(goal_data.get("id") or goal_data.get("goal_id") or "")
    if not goal_id:
        raise ValueError(f"A savings goal for user {user.id} is missing its id.")
    goal = session.get(SavingsGoal, goal_id)
    if goal is None:
        goal = SavingsGoal(id=goal_id, user_id=user.id)
        session.add(goal)
    goal.user_id = user.id
    goal.goal_name = str(goal_data.get("name") or goal_data.get("goal_name") or "Mục tiêu")
    goal.target_amount = max(1, int(goal_data.get("target_amount") or goal_data.get("target") or 1))
    goal.current_amount = max(0, int(goal_data.get("current_amount") or goal_data.get("current") or 0))
    goal.deadline = str(goal_data.get("deadline") or "2099-12-31")
    goal.icon = goal_data.get("icon")
    goal.color = goal_data.get("color")
    goal.category = goal_data.get("category")
    goal.ai_forecast = goal_data.get("ai_forecast")
    return goal


def _upsert_budget(session, user, category, amount, start_date, end_date):
    budget_id = f"{user.id}:{category.id}:MONTHLY:{start_date}"
    row = session.get(CategoryBudget, budget_id)
    if row is None:
        row = CategoryBudget(id=budget_id)
        session.add(row)
    row.user_id = user.id
    row.category_id = category.id
    row.amount_limit = max(0, int(amount))
    row.period = "MONTHLY"
    row.start_date = start_date
    row.end_date = end_date
    return row


def _serialize_category_name(value):
    return str(value or "").strip().casefold()


def _make_audit_log(session, log_data, users_by_name):
    actor = str(log_data.get("actor") or "system")
    user = users_by_name.get(actor.casefold())
    row = AuditLog(
        id=str(log_data.get("id") or ""),
        user_id=user.id if user else None,
        actor_name=actor,
        action=str(log_data.get("action") or "Unknown"),
        target=str(log_data.get("target") or "system"),
        result="Success" if str(log_data.get("result") or "Success").lower() in ("success", "succeeded") else "Failed",
        details=log_data.get("details"),
        ip=log_data.get("ip"),
        timestamp=str(log_data.get("timestamp") or datetime.now().isoformat()),
    )
    session.add(row)


def migrate_json_data():
    init_db()
    categories_data = _read_json("categories.json")
    users_data = _read_json("users.json")
    canonical_transactions = _read_json("mock_transactions.json")
    audit_data = _read_json("audit_logs.json")
    settings_data = _read_json("system_settings.json")

    with SessionLocal() as check_session:
        existing = any(
            check_session.query(model).limit(1).first() is not None
            for model in (User, BankConsent, Wallet, Transaction, Category)
        )
    if existing:
        raise RuntimeError(
            "The database already contains domain data; refusing to merge JSON over live records."
        )

    month_start, month_end = _date_range_for_month()
    with session_scope() as session:
        category_by_name = {}
        for item in categories_data:
            category_id = str(item.get("id") or "")
            if not category_id:
                raise ValueError("A category record is missing its id.")
            row = Category(
                id=category_id,
                category_name=str(item.get("name") or "Khác"),
                type=str(item.get("type") or "EXPENSE").upper(),
                bucket=str(item.get("bucket") or "WANTS").upper(),
                keywords_json=_dump_json(item.get("keywords") or []),
                icon=item.get("icon"),
                color=item.get("color"),
                is_default=int(bool(item.get("is_default", True))),
                is_hidden=int(bool(item.get("is_hidden", False))),
            )
            session.add(row)
            category_by_name[_serialize_category_name(row.category_name)] = row
        session.flush()

        users_by_id = {}
        users_by_name = {}
        user_source_by_id = {}
        consents_by_user = {}
        consents_by_id = {}
        wallets_by_user = {}
        wallet_by_account = {}
        round_up_goal_ids = {}
        for user_data in users_data:
            user = _upsert_user(session, user_data)
            users_by_id[user.id] = user
            users_by_name[user.username.casefold()] = user
            user_source_by_id[user.id] = user_data
            consents_by_user[user.id] = {}
            consents_by_id[user.id] = {}
            wallet_by_account[user.id] = {}
        session.flush()

        for user_data in users_data:
            user = users_by_id[str(user_data["id"])]
            user_consents = user_data.get("consents") or []
            by_provider = {}
            for consent_data in user_consents:
                consent = _upsert_consent(session, user, consent_data)
                if consent is None:
                    continue
                consents_by_user[user.id][consent.consent_id] = consent
                consents_by_id[user.id][consent.consent_id] = consent
                by_provider[consent.provider_code] = consent
            user_wallets = list(user_data.get("wallets") or [])
            existing_wallet_consents = {
                str(w.get("consentId") or w.get("consent_id"))
                for w in user_wallets
                if w.get("consentId") or w.get("consent_id")
            }
            for consent in consents_by_user[user.id].values():
                if consent.consent_id not in existing_wallet_consents:
                    source_consent = next(
                        (c for c in user_consents if str(c.get("consent_id")) == consent.consent_id),
                        {},
                    )
                    account_number = source_consent.get("account_no")
                    user_wallets.append({
                        "id": f"wallet_{user.id}_{consent.consent_id}",
                        "name": f"{consent.provider_name} · ****{str(account_number or '')[-4:]}",
                        "type": "ewallet" if consent.provider_code in ("MOMO", "ZALOPAY", "SHOPEEPAY") else "bank",
                        "bank_id": consent.provider_code,
                        "provider": consent.provider_name,
                        "account_no": account_number,
                        "initialBalance": 0,
                        "currentBalance": 0,
                        "managementMode": "connect",
                        "connectionStatus": "connected" if consent.status == "ACTIVE" else "disconnected",
                        "consentId": consent.consent_id,
                        "_consent_payload": source_consent,
                    })
            wallets_by_user[user.id] = {}
            for wallet_data in user_wallets:
                consent_id = str(wallet_data.get("consentId") or wallet_data.get("consent_id") or "")
                consent = consents_by_user[user.id].get(consent_id)
                if consent:
                    source_consent = next(
                        (c for c in user_consents if str(c.get("consent_id")) == consent_id),
                        {},
                    )
                    wallet_data = dict(wallet_data)
                    wallet_data["_consent_payload"] = source_consent
                wallet = _build_wallet(session, user, wallet_data, consents_by_user[user.id], by_provider)
                wallets_by_user[user.id][wallet.id] = wallet
                if wallet.account_no_masked:
                    wallet_by_account[user.id][wallet.account_no_masked] = wallet
                source_account = (wallet_data.get("_consent_payload") or {}).get("account_no")
                if source_account:
                    wallet_by_account[user.id][str(source_account)] = wallet
            goals_by_id = {}
            for goal_data in user_data.get("savings_goals") or []:
                goal = _upsert_goal(session, user, goal_data)
                goals_by_id[goal.id] = goal
            round_up = user_data.get("round_up") or {}
            target_goal_id = str(round_up.get("target_goal_id") or "")
            round_up_goal_ids[user.id] = target_goal_id if target_goal_id in goals_by_id else None

            budget_map = user_data.get("category_budgets") or user_data.get("category_limits") or {}
            for category_name, amount in budget_map.items():
                category = category_by_name.get(_serialize_category_name(category_name))
                if category is None:
                    raise ValueError(
                        f"Budget category {category_name!r} for {user.username} is missing from categories.json."
                    )
                _upsert_budget(session, user, category, amount, month_start, month_end)
        session.flush()
        for user_id, goal_id in round_up_goal_ids.items():
            users_by_id[user_id].round_up_goal_id = goal_id
        session.flush()

        baseline_user = next(
            (user for user in users_by_id.values() if user.username == BASELINE_USERNAME),
            None,
        )
        if baseline_user is None:
            raise ValueError(f"Baseline user {BASELINE_USERNAME!r} is missing.")
        baseline_wallets = wallets_by_user[baseline_user.id]
        for raw_txn in canonical_transactions:
            account_number = str(raw_txn.get("account_number") or "")
            wallet = wallet_by_account[baseline_user.id].get(account_number)
            if wallet is None:
                raise ValueError(
                    f"Cannot map baseline transaction {raw_txn.get('id')} to a wallet."
                )
            from modules.ai_categorizer import categorize_transaction

            category_result = categorize_transaction(
                raw_txn.get("description") or "",
                raw_txn.get("timestamp") or "",
                txn_type=raw_txn.get("type") or "OUTFLOW",
                categories=categories_data,
            )
            category = category_by_name.get(
                _serialize_category_name(category_result.get("category"))
            )
            session.add(Transaction(
                id=str(raw_txn.get("id")),
                wallet_id=wallet.id,
                category_id=category.id if category else None,
                timestamp=str(raw_txn.get("timestamp")),
                type=str(raw_txn.get("type") or "OUTFLOW").upper(),
                amount=int(raw_txn.get("amount") or 0),
                description=raw_txn.get("description"),
                source="OPEN_BANKING",
                reference_code=str(raw_txn.get("reference_code") or ""),
            ))

        # Transactions in this fixture are the canonical baseline; the three-month
        # JSON file is a separate alternative dataset and is intentionally not merged.
        for user_data in users_data:
            user = users_by_id[str(user_data["id"])]
            for txn_data in user_data.get("custom_transactions") or []:
                txn_id = str(txn_data.get("id") or "")
                if not txn_id:
                    raise ValueError(f"A custom transaction for {user.username} is missing its id.")
                source_value = str(txn_data.get("source") or "MANUAL").upper()
                txn_source = "OPEN_BANKING" if source_value.startswith("OPEN_BANKING") else source_value
                wallet_id = None
                bank = str(txn_data.get("bank") or txn_data.get("provider") or "").casefold()
                for candidate in wallets_by_user[user.id].values():
                    consent = consents_by_id[user.id].get(candidate.consent_id or "")
                    if bank and (
                        bank in candidate.wallet_name.casefold()
                        or bank == (candidate.provider_code or "").casefold()
                        or (consent and bank in consent.provider_name.casefold())
                    ):
                        wallet_id = candidate.id
                        break
                category_name = txn_data.get("ai_category") or txn_data.get("category")
                category = category_by_name.get(_serialize_category_name(category_name))
                reference = txn_data.get("reference_code")
                if txn_source == "OPEN_BANKING" and (wallet_id is None or not reference):
                    raise ValueError(
                        f"Open Banking transaction {txn_id} lacks a wallet or reference code."
                    )
                session.add(Transaction(
                    id=txn_id,
                    wallet_id=wallet_id,
                    category_id=category.id if category else None,
                    timestamp=str(txn_data.get("timestamp") or datetime.now().isoformat()),
                    type=str(txn_data.get("type") or "OUTFLOW").upper(),
                    amount=int(txn_data.get("amount") or 0),
                    description=txn_data.get("description"),
                    source=txn_source if txn_source in ("OPEN_BANKING", "MANUAL", "OCR", "PIS_SAVINGS") else "MANUAL",
                    reference_code=reference,
                    receipt_meta_json=_dump_json(txn_data["receipt_meta"]) if txn_data.get("receipt_meta") else None,
                ))

        # Update wallet balances based on transactions
        session.flush()
        for user_id, wallets in wallets_by_user.items():
            for wallet_id, wallet in wallets.items():
                net_txn_amount = (
                    session.query(func.sum(
                        case(
                            (Transaction.type == "INFLOW", Transaction.amount),
                            else_=-Transaction.amount,
                        )
                    ))
                    .filter(Transaction.wallet_id == wallet_id)
                    .scalar()
                    or 0
                )
                wallet.current_balance = wallet.initial_balance + net_txn_amount

        # Verify baseline data integrity
        session.flush()
        transaction_count = (
            session.query(func.count(Transaction.id))
            .join(Wallet, Transaction.wallet_id == Wallet.id)
            .filter(Wallet.user_id == baseline_user.id, Transaction.source == "OPEN_BANKING")
            .scalar()
        )
        net_amount = (
            session.query(func.sum(
                case(
                    (Transaction.type == "INFLOW", Transaction.amount),
                    else_=-Transaction.amount,
                )
            ))
            .join(Wallet, Transaction.wallet_id == Wallet.id)
            .filter(Wallet.user_id == baseline_user.id, Transaction.source == "OPEN_BANKING")
            .scalar()
            or 0
        )
        wallet_balance = (
            session.query(func.sum(Wallet.current_balance))
            .filter(Wallet.user_id == baseline_user.id)
            .scalar()
            or 0
        )
        if transaction_count != EXPECTED_BASELINE["transactions"]:
            raise ValueError(
                f"Baseline transaction count mismatch: {transaction_count} != "
                f"{EXPECTED_BASELINE['transactions']}."
            )
        if net_amount != EXPECTED_BASELINE["net_balance"]:
            raise ValueError(
                f"Baseline net transaction amount mismatch: {net_amount} != "
                f"{EXPECTED_BASELINE['net_balance']}."
            )
        if wallet_balance != EXPECTED_BASELINE["final_balance"]:
            raise ValueError(
                f"Baseline wallet balance mismatch: {wallet_balance} != "
                f"{EXPECTED_BASELINE['final_balance']}."
            )
        if baseline_user.monthly_income != EXPECTED_BASELINE["monthly_income"]:
            raise ValueError(
                f"Baseline monthly income mismatch: {baseline_user.monthly_income} != "
                f"{EXPECTED_BASELINE['monthly_income']}."
            )

        users_by_name = {user.username.casefold(): user for user in users_by_id.values()}
        for log_data in audit_data:
            _make_audit_log(session, log_data, users_by_name)

        now = datetime.now().isoformat(timespec="seconds")
        descriptions = {
            "app_name": "Tên ứng dụng",
            "app_version": "Phiên bản ứng dụng",
            "currency": "Đơn vị tiền tệ hiển thị",
            "date_format": "Định dạng ngày",
            "session_timeout_minutes": "Thời hạn phiên đăng nhập",
            "min_password_length": "Độ dài mật khẩu tối thiểu",
            "open_banking_sandbox": "Chế độ Open Banking sandbox",
            "compliance_standard": "Chuẩn tuân thủ",
        }
        for key, value in settings_data.items():
            data_type, stored_value = _system_setting_value(value)
            session.add(SystemSetting(
                key=str(key),
                value=stored_value,
                data_type=data_type,
                description=descriptions.get(str(key)),
                updated_at=now,
            ))

        credit_account_count = session.query(func.count(CreditAccount.id)).scalar() or 0
        return {
            "users": len(users_by_id),
            "wallets": sum(len(wallets) for wallets in wallets_by_user.values()),
            "transactions": transaction_count,
            "categories": len(categories_data),
            "audits": len(audit_data),
            "settings": len(settings_data),
            "credit_accounts": credit_account_count,
            "baseline_net": net_amount,
            "baseline_wallet_balance": wallet_balance,
        }


if __name__ == "__main__":
    result = migrate_json_data()
    print("JSON migration completed.")
    for key, value in result.items():
        print(f"{key}: {value}")
