"""
Test script để debug OCR transaction save
Kiểm tra:
1. Transactions có được lưu vào database không?
2. _user_dict có load được transactions từ DB không?
3. Format có đúng không?
"""

from modules.database import SessionLocal, Transaction, User, Wallet, Category
from modules.auth import _user_dict
import json

def test_transactions_in_db():
    """Kiểm tra transactions trong database"""
    print("\n" + "="*60)
    print("TEST 1: Kiểm tra Transactions trong Database")
    print("="*60)
    
    with SessionLocal() as db:
        # Đếm tổng số transactions
        total_txns = db.query(Transaction).count()
        print(f"✓ Tổng số transactions: {total_txns}")
        
        # Đếm theo source
        manual_count = db.query(Transaction).filter(Transaction.source == "MANUAL").count()
        ocr_count = db.query(Transaction).filter(Transaction.source == "OCR").count()
        openbanking_count = db.query(Transaction).filter(Transaction.source == "OPEN_BANKING").count()
        
        print(f"  - MANUAL: {manual_count}")
        print(f"  - OCR: {ocr_count}")
        print(f"  - OPEN_BANKING: {openbanking_count}")
        
        # Hiển thị 5 transactions gần nhất
        recent_txns = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(5).all()
        print(f"\n✓ 5 Transactions gần nhất:")
        for txn in recent_txns:
            wallet_name = txn.wallet.wallet_name if txn.wallet else "No wallet"
            category_name = txn.category.category_name if txn.category else "No category"
            print(f"  - {txn.id[:20]}... | {txn.timestamp} | {txn.source} | {txn.amount:,}đ")
            print(f"    Wallet: {wallet_name} | Category: {category_name}")
            print(f"    Desc: {txn.description[:60] if txn.description else 'N/A'}")

def test_user_dict_loading():
    """Kiểm tra _user_dict có load transactions đúng không"""
    print("\n" + "="*60)
    print("TEST 2: Kiểm tra _user_dict() load transactions")
    print("="*60)
    
    with SessionLocal() as db:
        # Lấy user đầu tiên
        user_row = db.query(User).first()
        if not user_row:
            print("❌ Không tìm thấy user nào trong database!")
            return
        
        print(f"✓ Testing với user: {user_row.username} (ID: {user_row.id})")
        
        # Test _user_dict
        try:
            user_dict = _user_dict(db, user_row)
            custom_txns = user_dict.get('custom_transactions', [])
            
            print(f"✓ custom_transactions có {len(custom_txns)} giao dịch")
            
            if len(custom_txns) > 0:
                print(f"\n✓ 3 giao dịch đầu tiên:")
                for txn in custom_txns[:3]:
                    print(f"  - ID: {txn.get('id')[:20]}...")
                    print(f"    Timestamp: {txn.get('timestamp')}")
                    print(f"    Amount: {txn.get('amount'):,}đ")
                    print(f"    Bank: {txn.get('bank')}")
                    print(f"    Category: {txn.get('category')}")
                    print(f"    Source: {txn.get('source')}")
                    print(f"    Description: {txn.get('description')[:50] if txn.get('description') else 'N/A'}")
                    print()
            else:
                print("⚠️  custom_transactions rỗng!")
                
                # Kiểm tra xem user có wallet không
                print(f"\nDebug info:")
                print(f"  - User có {len(user_row.wallets)} wallets")
                if user_row.wallets:
                    for w in user_row.wallets:
                        txn_count = db.query(Transaction).filter(Transaction.wallet_id == w.id).count()
                        print(f"    Wallet '{w.wallet_name}': {txn_count} transactions")
                        
        except Exception as e:
            print(f"❌ Lỗi khi gọi _user_dict: {e}")
            import traceback
            traceback.print_exc()

def test_wallet_transaction_link():
    """Kiểm tra liên kết giữa User -> Wallet -> Transaction"""
    print("\n" + "="*60)
    print("TEST 3: Kiểm tra liên kết User -> Wallet -> Transaction")
    print("="*60)
    
    with SessionLocal() as db:
        users = db.query(User).all()
        print(f"✓ Tổng số users: {len(users)}")
        
        for user in users[:3]:  # Chỉ test 3 users đầu
            print(f"\n✓ User: {user.username} (ID: {user.id})")
            print(f"  - Wallets: {len(user.wallets)}")
            
            total_txns = 0
            for wallet in user.wallets:
                txn_count = len(wallet.transactions)
                total_txns += txn_count
                if txn_count > 0:
                    print(f"    Wallet '{wallet.wallet_name}': {txn_count} transactions")
            
            print(f"  - Tổng transactions: {total_txns}")

def test_categories():
    """Kiểm tra categories có đủ không"""
    print("\n" + "="*60)
    print("TEST 4: Kiểm tra Categories")
    print("="*60)
    
    with SessionLocal() as db:
        categories = db.query(Category).all()
        print(f"✓ Tổng số categories: {len(categories)}")
        
        # Hiển thị một số categories
        print(f"\nCategories (10 đầu tiên):")
        for cat in categories[:10]:
            print(f"  - {cat.category_name} ({cat.type}) - Bucket: {cat.bucket}")

if __name__ == "__main__":
    try:
        test_transactions_in_db()
        test_user_dict_loading()
        test_wallet_transaction_link()
        test_categories()
        
        print("\n" + "="*60)
        print("✅ TEST HOÀN TẤT")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ LỖI NGHIÊM TRỌNG: {e}")
        import traceback
        traceback.print_exc()
