# server/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class SensorVectorSync(BaseModel):
    id: int
    user_id: int
    device_id: int
    timestamp: datetime

    heart_rate: Optional[int] = None
    hrv_rmssd: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    spo2: CrisOptional[int] = None
    skin_temperature: Optional[float] = None

    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    steps_count: Optional[int] = None

    noise_level_db: Optional[float] = None
    breathing_rate: Optional[int] = None

    activity_type: Optional[str] = None
    location_type: Optional[str] = None
    battery_level: Optional[int] = None

    stress_level: Optional[float] = None
    energy_level: Optional[float] = None
    focus_level: Optional[float] = None
    model_version: str
    confidence_score: Optional[float] = None

    raw_features: Optional[Dict[str, Any]] = None
    lora_weights: Optional[Dict[str, Any]] = None
    signal_quality: Optional[int] = None