# server/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# === ЗАГРУЖАЕМ .env ===
load_dotenv()  # Читает .env из корня проекта

# === НАСТРОЙКИ ===
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in .env")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# === ДВИЖОК ===
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# === БАЗА ===
class Base(DeclarativeBase):
    pass

# === ЗАВИСИМОСТЬ ===
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# === Pydantic ===
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    user_type: str = "free"  # ИСПРАВЛЕНО: убрано ".future"

class User(BaseModel):
    id: int
    username: str
    email: str
    user_type: str
    subscription_end: Optional[datetime]

class VectorData(BaseModel):
    device_id: str
    timestamp: datetime
    heart_rate: Optional[int] = None
    hrv: Optional[float] = None
    accel_x: float
    accel_y: float
    accel_z: float
    temperature: Optional[float] = None
    stress_level: Optional[float] = None
    model_weights: Optional[dict] = None

class Token(BaseModel):
    access_token: str
    token_type: str

# === SQLAlchemy ===
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    user_type = Column(String, server_default="free")  # ИСПРАВЛЕНО: просто строка
    subscription_end = Column(DateTime)

class VectorDB(Base):
    __tablename__ = "vectors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    device_id = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())  # ИСПРАВЛЕНО: func.now()
    data = Column(JSON)
    model_weights = Column(JSON, nullable=True)

# === FastAPI ===
app = FastAPI(title="Health Monitor API")

# === Токен ===
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# === Эндпоинты ===
@app.get("/")
async def root():
    return {"message": "API is running with asyncpg + .env!"}

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(UserDB).where(UserDB.username == user.username))
    db_user = result.scalars().first()
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
    await db.commit()
    await db.refresh(db_user)

    access_token = jwt.encode(
        {
            "sub": user.username,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # ИСПРАВЛЕНО: правильный exp
        },
        SECRET_KEY,  # ИСПРАВЛЕНО: SECRET_KEY без фигурных скобок
        algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        user_type=user.user_type,
        subscription_end=user.subscription_end
    )