from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime, Boolean, JSON, BigInteger, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    user_type = Column(String(20), default="free")
    subscription_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    devices = relationship("Device", back_populates="user")
    vectors = relationship("SensorVector", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_name = Column(String(100), nullable=False)
    device_type = Column(String(20))
    device_id = Column(String(100), unique=True, nullable=False)  # MAC or UUID
    os_version = Column(String(50))
    app_version = Column(String(20))
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="devices")
    vectors = relationship("SensorVector", back_populates="device")


class SensorVector(Base):
    __tablename__ = "sensor_vectors"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Biometrics
    heart_rate = Column(Integer)
    hrv_rmssd = Column(Float)
    hrv_sdnn = Column(Float)
    spo2 = Column(Integer)
    skin_temperature = Column(Float)

    # Motion
    accel_x = Column(Float)
    accel_y = Column(Float)
    accel_z = Column(Float)
    gyro_x = Column(Float)
    gyro_y = Column(Float)
    gyro_z = Column(Float)
    steps_count = Column(Integer, default=0)

    # Audio
    noise_level_db = Column(Float)
    breathing_rate = Column(Integer)

    # Context
    activity_type = Column(String(50))
    location_type = Column(String(20))
    battery_level = Column(Integer)

    # ML Results
    stress_level = Column(Float)
    energy_level = Column(Float)
    focus_level = Column(Float)
    model_version = Column(String(20), nullable=False)
    confidence_score = Column(Float)

    # Flexible storage
    raw_features = Column(JSONB)
    lora_weights = Column(JSONB)
    signal_quality = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="vectors")
    device = relationship("Device", back_populates="vectors")


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    model_type = Column(String(50), nullable=False)
    model_format = Column(String(20), default="onnx")
    model_size_bytes = Column(BigInteger)
    checksum = Column(String(64))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB)


class LoraUpdate(Base):
    __tablename__ = "lora_updates"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ml_models.id"))
    lora_weights = Column(JSONB, nullable=False)
    update_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    training_samples = Column(Integer, nullable=False)
    validation_accuracy = Column(Float)
    metadata = Column(JSONB)


class UserLabel(Base):
    __tablename__ = "user_labels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vector_id = Column(BigInteger, ForeignKey("sensor_vectors.id"))
    label_type = Column(String(50), nullable=False)
    label_value = Column(String(50), nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    note = Column(String)


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_type = Column(String(20))
    model_version_before = Column(String(20))
    model_version_after = Column(String(20))
    samples_used = Column(Integer, nullable=False)
    epochs = Column(Integer, nullable=False)
    learning_rate = Column(Float)
    validation_loss = Column(Float)
    validation_accuracy = Column(Float)
    status = Column(String(20), default="completed")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    metadata = Column(JSONB)
    error_message = Column(String)