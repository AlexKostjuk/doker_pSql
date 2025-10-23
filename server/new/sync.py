# server/sync.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .schemas import SensorVectorSync
from .models import SensorVector, User, Device
from .database import get_db
from .auth import verify_token

router = APIRouter()

@router.post("/sync")
async def sync_vectors(
    vectors: List[SensorVectorSync],
    db: AsyncSession = Depends(get_db),
    username: str = Depends(verify_token)
):
    # Проверка пользователя
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.user_type != "premium":
        raise HTTPException(403, "PREMIUM only")

    # Проверка device_id
    device_ids = {v.device_id for v in vectors}
    result = await db.execute(select(Device.id).where(Device.id.in_(device_ids), Device.user_id == user.id))
    valid_device_ids = {row[0] for row in result.fetchall()}

    synced = 0
    for v in vectors:
        if v.device_id not in valid_device_ids:
            continue

        db_vector = SensorVector(**v.dict())
        db.add(db_vector)
        synced += 1

    await db.commit()
    return {"status": "synced", "count": synced}