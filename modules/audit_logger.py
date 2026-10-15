import json
import os
import time
from datetime import datetime

AUDIT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'audit_logs.json')

def load_audit_logs():
    if not os.path.exists(AUDIT_FILE):
        return []
    try:
        with open(AUDIT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_audit_logs(logs):
    try:
        with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving audit log: {e}")

def log_action(actor, action, target, result="Success", details="", ip="127.0.0.1"):
    """
    Ghi nhận nhật ký sự kiện hệ thống tuân thủ Nghị định 13/2023/NĐ-CP
    actor: Tên người dùng / Admin thực hiện
    action: Hành động (ví dụ: 'Đăng nhập Admin', 'Khóa tài khoản', 'Thêm danh mục'...)
    target: Đối tượng bị tác động (User ID, Category ID, System...)
    result: 'Success' hoặc 'Failed'
    details: Ghi chú ngắn gọn
    ip: Địa chỉ IP
    """
    logs = load_audit_logs()
    
    event_entry = {
        "id": f"LOG_{int(time.time() * 1000) % 10000000}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": actor or "system",
        "action": action,
        "target": target or "system",
        "result": result,
        "details": details,
        "ip": ip
    }
    
    # Đưa sự kiện mới nhất lên đầu danh sách
    logs.insert(0, event_entry)
    
    # Giới hạn tối đa 500 bản ghi để giữ dung lượng nhẹ
    if len(logs) > 500:
        logs = logs[:500]
        
    save_audit_logs(logs)
    return event_entry

def get_audit_logs(limit=100, action_filter=None, actor_filter=None):
    logs = load_audit_logs()
    if action_filter and action_filter != 'ALL':
        logs = [l for l in logs if l.get('action') == action_filter]
    if actor_filter:
        logs = [l for l in logs if actor_filter.lower() in l.get('actor', '').lower()]
    return logs[:limit]
