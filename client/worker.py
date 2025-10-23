# client/worker.py
from PyQt6.QtCore import QThread, pyqtSignal
from .db import get_db
from .local_models import SensorVector
import random
from datetime import datetime
import time

class DatabaseWorker(QThread):
    data_collected = pyqtSignal(dict)
    log_message = pyqtSignal(str)

    def __init__(self, user_id, device_id):
        super().__init__()
        self.user_id = user_id
        self.device_id = device_id
        self.running = True

    def run(self):
        while self.running:
            self.collect_data()
            time.sleep(5)

    def collect_data(self):
        db_gen = get_db()
        db = next(db_gen)
        try:
            vector = SensorVector(
                id=random.randint(1000000, 9999999),
                user_id=self.user_id,
                device_id=self.device_id,
                timestamp=datetime.utcnow(),
                heart_rate=random.randint(60, 100),
                hrv_rmssd=round(random.uniform(20, 80), 2),
                spo2=random.randint(95, 100),
                stress_level=round(random.uniform(0, 1), 2),
                model_version="v1.0",
                confidence_score=round(random.uniform(0.7, 0.99), 2),
                steps_count=random.randint(0, 50)
            )
            db.add(vector)
            db.commit()

            data = {"hr": vector.heart_rate, "stress": vector.stress_level}
            self.data_collected.emit(data)
            self.log_message.emit(f"HR={vector.heart_rate}, Stress={vector.stress_level:.2f}")

        except Exception as e:
            db.rollback()
            self.log_message.emit(f"[ERROR] {e}")
        finally:
            db.close()

    def stop(self):
        self.running = False