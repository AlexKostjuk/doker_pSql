# client/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .local_models import Base
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "health_local.db")
engine = create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()