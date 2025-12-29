
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.database import get_db

app = FastAPI(title="EGE Tracker API")

@app.post("/users/", response_model=schemas.UserResponse)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db, user)

@app.post("/scores/", response_model=schemas.ScoreResponse)
async def add_score(score: schemas.ScoreCreate, db: AsyncSession = Depends(get_db)):
    result = await crud.add_or_update_score(db, score)
    if not result:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    return result

@app.get("/scores/{telegram_id}", response_model=list[schemas.ScoreResponse])
async def get_scores(telegram_id: int, db: AsyncSession = Depends(get_db)):
    scores = await crud.get_user_scores(db, telegram_id)
    return scores
