import uuid
from datetime import datetime

from modules.database import AuditLog, SessionLocal, User


def _entry(row):
    return {
        "id": row.id,
        "timestamp": row.timestamp,
        "actor": row.actor_name,
        "action": row.action,
        "target": row.target,
        "result": row.result,
        "details": row.details or "",
        "ip": row.ip or "",
    }


def load_audit_logs():
    with SessionLocal() as db:
        rows = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).all()
        return [_entry(row) for row in rows]


def save_audit_logs(logs):
    """Compatibility import helper used to restore or seed audit history."""
    with SessionLocal() as db:
        try:
            for item in logs:
                row = db.get(AuditLog, str(item.get("id") or ""))
                if row is None:
                    row = AuditLog(id=str(item.get("id") or f"LOG_{uuid.uuid4().hex}"))
                    db.add(row)
                actor = str(item.get("actor") or "system")
                user = db.query(User).filter(User.username == actor).first()
                row.user_id = user.id if user else None
                row.actor_name = actor
                row.action = str(item.get("action") or "UNKNOWN")
                row.target = str(item.get("target") or "system")
                row.result = str(item.get("result") or "Success")
                row.details = str(item.get("details") or "")
                row.ip = item.get("ip")
                row.timestamp = str(item.get("timestamp") or datetime.now().isoformat(timespec="seconds"))
            db.commit()
        except Exception:
            db.rollback()
            raise


def log_action(actor, action, target, result="Success", details="", ip="127.0.0.1"):
    actor_name = str(actor or "system")
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == actor_name).first()
        entry = AuditLog(
            id=f"LOG_{uuid.uuid4().hex}",
            user_id=user.id if user else None,
            actor_name=actor_name,
            action=str(action),
            target=str(target or "system"),
            result=str(result),
            details=str(details or ""),
            ip=ip,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.add(entry)
        db.commit()
        return _entry(entry)


def get_audit_logs(limit=100, action_filter=None, actor_filter=None):
    with SessionLocal() as db:
        query = db.query(AuditLog)
        if action_filter and action_filter != "ALL":
            query = query.filter(AuditLog.action == action_filter)
        if actor_filter:
            query = query.filter(AuditLog.actor_name.ilike(f"%{actor_filter}%"))
        rows = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit).all()
        return [_entry(row) for row in rows]
