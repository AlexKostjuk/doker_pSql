# client/sync.py
import requests
from .db import get_db
from .local_models import SensorVector
from sqlalchemy import delete

def sync_to_cloud(jwt_token: str, api_url: str = "http://localhost:8000/sync"):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    db = next(get_db())
    try:
        vectors = db.query(SensorVector).all()
        data = []
        for v in vectors:
            item = {
                "id": v.id,
                "user_id": v.user_id,
                "device_id": v.device_id,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                "heart_rate": v.heart_rate,
                "hrv_rmssd": v.hrv_rmssd,
                "hrv_sdnn": v.hrv_sdnn,
                "spo2": v.spo2,
                "skin_temperature": v.skin_temperature,
                "accel_x": v.accel_x,
                "accel_y": v.accel_y,
                "accel_z": v.accel_z,
                "gyro_x": v.gyro_x,
                "gyro_y": v.gyro_y,
                "gyro_z": v.gyro_z,
                "steps_count": v.steps_count,
                "noise_level_db": v.noise_level_db,
                "breathing_rate": v.breathing_rate,
                "activity_type": v.activity_type,
                "location_type": v.location_type,
                "battery_level": v.battery_level,
                "stress_level": v.stress_level,
                "energy_level": v.energy_level,
                "focus_level": v.focus_level,
                "model_version": v.model_version,
                "confidence_score": v.confidence_score,
                "raw_features": v.raw_features,
                "lora_weights": v.lora_weights,
                "signal_quality": v.signal_quality,
            }
            data.append(item)

        if not data:
            print("[SYNC] Нет данных для синхронизации")
            return

        response = requests.post(api_url, json=data, headers=headers)
        if response.status_code == 200:
            # Удалить после успешной отправки
            stmt = delete(SensorVector)  # ← ПРАВИЛЬНО
            db.execute(stmt)
            db.commit()
            print(f"[SYNC] Успешно отправлено и удалено {len(data)} записей")
        else:
            print(f"[SYNC] Ошибка: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[ERROR] Синхронизация: {e}")
    finally:
        db.close()