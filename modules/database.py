import os
from contextlib import contextmanager
from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(_DATA_DIR, exist_ok=True)
DATABASE_URL = os.environ.get(
    "FINLAB_DATABASE_URL",
    "sqlite:///" + os.path.join(_DATA_DIR, "finlab.db").replace("\\", "/"),
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'locked')", name="ck_users_status"),
        CheckConstraint(
            "needs_ratio + wants_ratio + savings_ratio = 100",
            name="ck_users_budget_ratio_total",
        ),
        CheckConstraint(
            "needs_ratio BETWEEN 0 AND 100 AND wants_ratio BETWEEN 0 AND 100 "
            "AND savings_ratio BETWEEN 0 AND 100",
            name="ck_users_budget_ratio_range",
        ),
        CheckConstraint("round_up_enabled IN (0, 1)", name="ck_users_round_up_enabled"),
        CheckConstraint("round_up_step > 0", name="ck_users_round_up_step"),
        CheckConstraint("round_up_accumulated >= 0", name="ck_users_round_up_accumulated"),
    )

    id = Column(String(64), primary_key=True)
    username = Column(String(128), nullable=False, unique=True)
    password_hash = Column(String(512), nullable=False)
    password_salt = Column(LargeBinary, nullable=False)
    full_name = Column(String(256), nullable=False)
    email = Column(String(320), nullable=False, unique=True)
    phone = Column(String(32), unique=True)
    role = Column(String(16), nullable=False, default="user")
    status = Column(String(16), nullable=False, default="active")
    created_at = Column(String(40), nullable=False)
    occupation = Column(String(256))
    monthly_income = Column(Integer)
    needs_ratio = Column(Integer, nullable=False, default=50)
    wants_ratio = Column(Integer, nullable=False, default=30)
    savings_ratio = Column(Integer, nullable=False, default=20)
    onboarding_goals_json = Column(Text, nullable=False, default="[]")
    round_up_enabled = Column(Integer, nullable=False, default=0)
    round_up_step = Column(Integer, nullable=False, default=1000)
    round_up_accumulated = Column(Integer, nullable=False, default=0)
    round_up_goal_id = Column(
        String(64), ForeignKey("savings_goals.id", ondelete="SET NULL")
    )

    bank_consents = relationship(
        "BankConsent", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="BankConsent.user_id",
    )
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    savings_goals = relationship(
        "SavingsGoal", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="SavingsGoal.user_id",
    )
    category_budgets = relationship(
        "CategoryBudget", back_populates="user", cascade="all, delete-orphan"
    )
    credit_accounts = relationship(
        "CreditAccount", back_populates="user", cascade="all, delete-orphan"
    )
    round_up_goal = relationship("SavingsGoal", foreign_keys=[round_up_goal_id])


class BankConsent(Base):
    __tablename__ = "bank_consents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED')",
            name="ck_bank_consents_status",
        ),
    )

    consent_id = Column(String(128), primary_key=True)
    user_id = Column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_code = Column(String(32), nullable=False, index=True)
    provider_name = Column(String(256), nullable=False)
    scopes = Column(Text, nullable=False, default="[]")
    granted_at = Column(String(40), nullable=False)
    expires_at = Column(String(40), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="ACTIVE", index=True)
    compliance = Column(Text)
    standard = Column(Text)
    encrypted_token = Column(LargeBinary)

    user = relationship("User", back_populates="bank_consents")
    wallets = relationship("Wallet", back_populates="consent")


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "account_no_hash", name="uq_wallet_user_account_hash"),
        CheckConstraint(
            "initial_balance >= 0 AND current_balance >= 0",
            name="ck_wallets_nonnegative_balances",
        ),
        CheckConstraint(
            "wallet_type IN ('CASH', 'E_WALLET', 'BANK')",
            name="ck_wallets_type",
        ),
        CheckConstraint(
            "connection_status IN ('MANUAL', 'CONNECTED', 'DISCONNECTED', 'ERROR', 'ARCHIVED')",
            name="ck_wallets_connection_status",
        ),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_id = Column(
        String(128), ForeignKey("bank_consents.consent_id", ondelete="SET NULL"), index=True
    )
    wallet_name = Column(String(256), nullable=False)
    wallet_type = Column(String(16), nullable=False, default="CASH", index=True)
    provider_code = Column(String(32))
    account_no_encrypted = Column(LargeBinary)
    account_no_masked = Column(String(64))
    account_no_hash = Column(String(64))
    initial_balance = Column(Integer, nullable=False, default=0)
    current_balance = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="VND")
    connection_status = Column(
        String(16), nullable=False, default="MANUAL", index=True
    )
    note = Column(Text)
    created_at = Column(String(40))
    updated_at = Column(String(40))
    last_synced_at = Column(String(40))

    user = relationship("User", back_populates="wallets")
    consent = relationship("BankConsent", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("category_name", "type", name="uq_categories_name_type"),
        CheckConstraint("is_hidden IN (0, 1)", name="ck_categories_is_hidden"),
        CheckConstraint("is_default IN (0, 1)", name="ck_categories_is_default"),
        CheckConstraint("type IN ('INCOME', 'EXPENSE')", name="ck_categories_type"),
        CheckConstraint(
            "bucket IN ('INCOME', 'NEEDS', 'WANTS', 'SAVINGS')",
            name="ck_categories_bucket",
        ),
    )

    id = Column(String(64), primary_key=True)
    category_name = Column(String(256), nullable=False, index=True)
    type = Column(String(16), nullable=False, index=True)
    bucket = Column(String(16), nullable=False, index=True)
    keywords_json = Column(Text)
    icon = Column(String(128))
    color = Column(String(32))
    is_default = Column(Integer, nullable=False, default=1)
    is_hidden = Column(Integer, nullable=False, default=0)

    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("CategoryBudget", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "reference_code", name="uq_transactions_wallet_reference"),
        CheckConstraint("amount > 0", name="ck_transactions_positive_amount"),
        CheckConstraint("type IN ('INFLOW', 'OUTFLOW')", name="ck_transactions_type"),
        CheckConstraint(
            "source IN ('OPEN_BANKING', 'MANUAL', 'OCR', 'PIS_SAVINGS')",
            name="ck_transactions_source",
        ),
        CheckConstraint(
            "source != 'OPEN_BANKING' OR (wallet_id IS NOT NULL AND reference_code IS NOT NULL)",
            name="ck_open_banking_transaction_wallet_reference",
        ),
    )

    id = Column(String(128), primary_key=True)
    wallet_id = Column(
        String(64), ForeignKey("wallets.id", ondelete="SET NULL"), index=True
    )
    category_id = Column(
        String(64), ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    timestamp = Column(String(40), nullable=False, index=True)
    type = Column(String(16), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    description = Column(Text)
    source = Column(String(32), nullable=False, default="MANUAL", index=True)
    reference_code = Column(String(128))
    receipt_meta_json = Column(Text)

    wallet = relationship("Wallet", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class CategoryBudget(Base):
    __tablename__ = "category_budgets"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "category_id", "period", "start_date",
            name="uq_category_budget_user_category_period_start",
        ),
        CheckConstraint("amount_limit >= 0", name="ck_category_budgets_nonnegative_limit"),
        CheckConstraint("end_date >= start_date", name="ck_category_budgets_valid_dates"),
        CheckConstraint(
            "period IN ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')",
            name="ck_category_budgets_period",
        ),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id = Column(
        String(64), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_limit = Column(Integer, nullable=False)
    period = Column(String(16), nullable=False, default="MONTHLY", index=True)
    start_date = Column(String(10), nullable=False, index=True)
    end_date = Column(String(10), nullable=False)

    user = relationship("User", back_populates="category_budgets")
    category = relationship("Category", back_populates="budgets")


class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_savings_goals_positive_target"),
        CheckConstraint("current_amount >= 0", name="ck_savings_goals_nonnegative_current"),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_name = Column(String(256), nullable=False)
    target_amount = Column(Integer, nullable=False)
    current_amount = Column(Integer, nullable=False, default=0)
    deadline = Column(String(40), nullable=False, index=True)
    icon = Column(String(128))
    color = Column(String(32))
    category = Column(String(128))
    ai_forecast = Column(Text)

    user = relationship("User", back_populates="savings_goals", foreign_keys=[user_id])


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (
        CheckConstraint("credit_limit > 0", name="ck_credit_accounts_positive_limit"),
        CheckConstraint("current_debt >= 0", name="ck_credit_accounts_nonnegative_debt"),
        CheckConstraint("apr_percent >= 0", name="ck_credit_accounts_nonnegative_apr"),
        CheckConstraint(
            "account_type IN ('CREDIT_CARD', 'INSTALLMENT')",
            name="ck_credit_accounts_type",
        ),
        CheckConstraint(
            "statement_day IS NULL OR statement_day BETWEEN 1 AND 31",
            name="ck_credit_accounts_statement_day",
        ),
        CheckConstraint("due_day BETWEEN 1 AND 31", name="ck_credit_accounts_due_day"),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_name = Column(String(256), nullable=False)
    account_type = Column(String(32), nullable=False, default="CREDIT_CARD")
    credit_limit = Column(Integer, nullable=False)
    current_debt = Column(Integer, nullable=False, default=0)
    apr_percent = Column(Float, nullable=False, default=0)
    statement_day = Column(Integer)
    due_day = Column(Integer, nullable=False, default=1, index=True)
    status = Column(String(16), nullable=False, default="ACTIVE", index=True)

    user = relationship("User", back_populates="credit_accounts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), index=True)
    actor_name = Column(String(256), nullable=False)
    action = Column(String(256), nullable=False, index=True)
    target = Column(Text, nullable=False)
    result = Column(String(16), nullable=False, index=True)
    details = Column(Text)
    ip = Column(String(64))
    timestamp = Column(String(40), nullable=False, index=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        CheckConstraint(
            "data_type IN ('STRING', 'INT', 'BOOL', 'JSON')",
            name="ck_system_settings_data_type",
        ),
    )

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    data_type = Column(String(16), nullable=False, default="STRING")
    description = Column(Text)
    updated_at = Column(String(40), nullable=False)
    updated_by = Column(String(256))


@contextmanager
def session_scope():
    """Commit a unit of work atomically; rollback and re-raise on failure."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)
