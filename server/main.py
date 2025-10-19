from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import os

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./health.db")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    user_type: str = "free"  # free or premium


class User(BaseModel):
    id: int
    username: str
    email: str
    user_type: str
    subscription_end: Optional[datetime]


class VectorData(BaseModel):
    device_id: str
    timestamp: datetime
    heart_rate: Optional[int]
    hrv: Optional[float]
    accel_x: float
    accel_y: float
    accel_z: float
    temperature: Optional[float]
    stress_level: Optional[float]
    model_weights: Optional[dict] = None


class Token(BaseModel):
    access_token: str
    token_type: str


# SQLAlchemy models
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    user_type = Column(String, default="free")
    subscription_end = Column(DateTime)


class VectorDB(Base):
    __tablename__ = "vectors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    device_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON)
    model_weights = Column(JSON, nullable=True)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Health Monitor API")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)
    db_user = UserDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        user_type=user.user_type
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = jwt.encode(
        {"sub": user.username, "type": "access"}, SECRET_KEY, algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
def read_users_me(username: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type,
        "subscription_end": user.subscription_end
    }


@app.post("/sync/{user_id}/vectors")
def upload_vectors(
        user_id: int,
        vectors: List[VectorData],
        username: str = Depends(verify_token),
        db: Session = Depends(get_db)
):
    # Verify user owns the data
    user = db.query(UserDB).filter(UserDB.id == user_id, UserDB.username == username).first()
    if not user or user.user_type != "premium":
        raise HTTPException(status_code=403, detail="Premium access required")

    for vector in vectors:
        db_vector = VectorDB(
            user_id=user_id,
            device_id=vector.device_id,
            data=vector.dict(exclude={"device_id", "timestamp"}),
            timestamp=vector.timestamp
        )
        db.add(db_vector)

    db.commit()
    return {"status": "synced", "count": len(vectors)}


@app.get("/sync/{user_id}/vectors")
def download_vectors(
        user_id: int,
        limit: int = 1000,
        username: str = Depends(verify_token),
        db: Session = Depends(get_db)
):
    user = db.query(UserDB).filter(UserDB.id == user_id, UserDB.username == username).first()
    if not user or user.user_type != "premium":
        raise HTTPException(status_code=403, detail="Premium access required")

    vectors = db.query(VectorDB).filter(
        VectorDB.user_id == user_id
    ).order_by(VectorDB.timestamp.desc()).limit(limit).all()

    return [{
        "device_id": v.device_id,
        "timestamp": v.timestamp,
        "data": v.data,
        "model_weights": v.model_weights
    } for v in vectors]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)