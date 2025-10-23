# server/main.py
from fastapi import FastAPI
from .database import engine
from .models import Base
from .auth import router as auth_router
from .sync import router as sync_router  # ← УБЕДИСЬ, ЧТО sync.py СУЩЕСТВУЕТ

app = FastAPI(title="Health Monitor API")

# Подключаем роутеры
app.include_router(auth_router)
app.include_router(sync_router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": "API is running!"}