import asyncio

import httpx
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import settings
from app.logger import setup_logger

logger = setup_logger("bot_tg")

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
router = Router()

class RegisterState(StatesGroup):
    waiting_for_name = State()

class ScoreState(StatesGroup):
    waiting_for_subject = State()
    waiting_for_score = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"ТГ Бот: Юзер {message.from_user.id} вызвал /start")
    await message.answer(
        "Привет! Я бот для учета баллов ЕГЭ.\n"
        "Доступные команды:\n"
        "/register - Регистрация\n"
        "/enter_scores - Ввести баллы\n"
        "/view_scores - Посмотреть мои баллы"
    )

# Регистрация
@router.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    logger.info(f"ТГ Бот: Юзер {message.from_user.id} начал /register")
    await message.answer("Введите Имя и Фамилию (например: Имя Фамилия):")
    await state.set_state(RegisterState.waiting_for_name)

@router.message(RegisterState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logger.info(f"ТГ Бот: Юзер {message.from_user.id} ввел имя: {message.text}")
    full_name = message.text
    parts = full_name.split()
    if len(parts) < 2:
        logger.warning(f"ТГ Бот: Юзер {message.from_user.id} ошибся в формате имени")
        await message.answer("Пожалуйста, введите Имя и Фамилию.")
        return

    first_name, last_name = parts[0], parts[1]
    telegram_id = message.from_user.id

    async with httpx.AsyncClient() as client:
        payload = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "last_name": last_name
        }
        try:
            logger.info(f"ТГ Бот: Отправка регистрации в API для {telegram_id}")
            response = await client.post(f"{settings.API_BASE_URL}/users/", json=payload)
            if response.status_code == 200:
                logger.info(f"ТГ Бот: Юзер {telegram_id} успешно создан")
                await message.answer(f"Ученик {first_name} {last_name} успешно зарегистрирован!")
            else:
                logger.error(f"ТГ Бот: Ошибка API {response.status_code} при регистрации {telegram_id}")
                await message.answer("Ошибка при регистрации на сервере.")
        except Exception as e:
            logger.error(f"ТГ Бот: Критическая ошибка соединения с API: {e}")
            await message.answer(f"Ошибка соединения: {e}")

    await state.clear()

# Ввод баллов
@router.message(Command("enter_scores"))
async def cmd_enter_scores(message: types.Message, state: FSMContext):
    logger.info(f"ТГ Бот: Юзер {message.from_user.id} вызвал /enter_scores")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Математика"), types.KeyboardButton(text="Русский язык")],
            [types.KeyboardButton(text="Информатика"), types.KeyboardButton(text="Физика")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выберите предмет:", reply_markup=keyboard)
    await state.set_state(ScoreState.waiting_for_subject)

@router.message(ScoreState.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    logger.info(f"ТГ Бот: Юзер {message.from_user.id} выбрал предмет {message.text}")
    await state.update_data(subject=message.text)
    await message.answer("Введите количество баллов (число):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(ScoreState.waiting_for_score)

@router.message(ScoreState.waiting_for_score)
async def process_score(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        logger.warning(f"ТГ Бот: Юзер {message.from_user.id} ввел не число в баллы: {message.text}")
        await message.answer("Пожалуйста, введите число.")
        return

    score = int(message.text)
    data = await state.get_data()
    subject = data['subject']
    telegram_id = message.from_user.id

    async with httpx.AsyncClient() as client:
        payload = {
            "telegram_id": telegram_id,
            "subject": subject,
            "score": score
        }
        try:
            logger.info(f"ТГ Бот: Отправка баллов в API для {telegram_id} ({subject})")
            response = await client.post(f"{settings.API_BASE_URL}/scores/", json=payload)
            if response.status_code == 200:
                logger.info(f"ТГ Бот: Баллы для {telegram_id} сохранены")
                await message.answer(f"Балл сохранен: {subject} - {score}")
            elif response.status_code == 404:
                logger.warning(f"ТГ Бот: Юзер {telegram_id} пытался ввести баллы без регистрации")
                await message.answer("Сначала нужно зарегистрироваться! (/register)")
            else:
                logger.error(f"ТГ Бот: Ошибка API {response.status_code} при вводе баллов")
                await message.answer("Ошибка сохранения.")
        except Exception as e:
            logger.error(f"ТГ Бот: Ошибка соединения при вводе баллов: {e}")
            await message.answer(f"Ошибка соединения: {e}")

    await state.clear()

# Просмотр баллов
@router.message(Command("view_scores"))
async def cmd_view_scores(message: types.Message):
    telegram_id = message.from_user.id
    logger.info(f"ТГ Бот: Юзер {telegram_id} запросил свои баллы")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.API_BASE_URL}/scores/{telegram_id}")
            if response.status_code == 200:
                scores = response.json()
                logger.info(f"ТГ Бот: Получено {len(scores)} предметов для {telegram_id}")
                if not scores:
                    await message.answer("У вас пока нет сохраненных баллов.")
                    return

                text = "Ваши баллы:\n"
                for item in scores:
                    text += f"-- {item['subject']}: {item['score']}\n"
                await message.answer(text)
            else:
                logger.error(f"ТГ Бот: Не удалось получить баллы для {telegram_id}, код {response.status_code}")
                await message.answer("Не удалось получить данные.")
        except Exception as e:
            logger.error(f"ТГ Бот: Ошибка сети при просмотре баллов: {e}")
            await message.answer(f"Ошибка соединения: {e}")

async def main():
    dp.include_router(router)
    logger.info("ТГ Бот: Запуск поллинга...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
