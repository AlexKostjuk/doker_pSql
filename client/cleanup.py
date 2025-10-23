# client/cleanup.py
from datetime import datetime, timedelta
from sqlalchemy import delete
from .local_models import SensorVector
from .db import get_db

FREE_STORAGE_DAYS = 60

def cleanup_old_data():
    cutoff = datetime.utcnow() - timedelta(days=FREE_STORAGE_DAYS)
    db_gen = get_db()
    db = next(db_gen)
    try:
        stmt = delete(SensorVector).where(SensorVector.timestamp < cutoff)
        result = db.execute(stmt)
        db.commit()
        print(f"[CLEANUP] Удалено {result.rowcount} записей старше {FREE_STORAGE_DAYS} дней")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Очистка: {e}")
    finally:
        db.close()