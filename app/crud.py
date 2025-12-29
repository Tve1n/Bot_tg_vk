from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import setup_logger
from app.models import Score, User
from app.schemas import ScoreCreate, UserCreate

logger = setup_logger("crud")

async def create_user(db: AsyncSession, user_in: UserCreate):

    logger.info(f"Запрос на создание пользователя: {user_in.telegram_id}")

    result = await db.execute(select(User).where(User.telegram_id == user_in.telegram_id))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.info(f"Пользователь {user_in.telegram_id} уже существует")
        return existing_user

    new_user = User(**user_in.model_dump())
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Создан новый пользователь: ID {new_user.id} (TG: {user_in.telegram_id})")
        return new_user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя {user_in.telegram_id}: {e}")
        await db.rollback()
        raise

async def add_or_update_score(db: AsyncSession, score_in: ScoreCreate):
    logger.info(f"Добавление/обновление баллов для {score_in.telegram_id}: {score_in.subject} = {score_in.score}")

    # Поиск юзера по telegram_id
    result = await db.execute(select(User).where(User.telegram_id == score_in.telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Юзер {score_in.telegram_id} не найден. Невозможно добавить баллы.")
        return None

    # Поиск балла по предмету
    result = await db.execute(
        select(Score).where(Score.user_id == user.id, Score.subject == score_in.subject)
    )
    existing_score = result.scalar_one_or_none()

    if existing_score:
        logger.info(f"Обновляем существующий балл для юзера {user.id} по предмету {score_in.subject}")
        existing_score.score = score_in.score
        await db.commit()
        return existing_score
    else:
        logger.info(f"Создаем новую запись балла для юзера {user.id} по предмету {score_in.subject}")
        new_score = Score(user_id=user.id, subject=score_in.subject, score=score_in.score)
        db.add(new_score)
        await db.commit()
        await db.refresh(new_score)
        return new_score

async def get_user_scores(db: AsyncSession, telegram_id: int):
    logger.info(f"Запрос списка всех баллов для TG ID: {telegram_id}")

    # Получаем юзера и подгружаем его баллы
    result = await db.execute(
        select(Score)
        .join(User)
        .where(User.telegram_id == telegram_id)
    )
    scores = result.scalars().all()
    logger.info(f"Найдено предметов для {telegram_id}: {len(scores)}")
    return scores
