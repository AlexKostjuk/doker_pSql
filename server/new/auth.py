# server/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter()
security = HTTPBearer()

async def verify_token(credentials: HTTPBearer = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(401, "Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")