import httpx
from vkbottle import BaseStateGroup, CtxStorage
from vkbottle.bot import Bot, Message

from app.config import settings
from app.logger import setup_logger

logger = setup_logger("vk_bot")

bot = Bot(token=settings.VK_TOKEN)
ctx_storage = CtxStorage()

class RegisterState(BaseStateGroup):
    NAME = 0

class ScoreState(BaseStateGroup):
    SUBJECT = 0
    SCORE = 1

@bot.on.private_message(text=["/start", "Начать"])
async def start_handler(message: Message):
    logger.info(f"ВК Бот: Юзер {message.from_id} вызвал /start")
    await message.answer(
        "Привет! Это ЕГЭ Трекер.\n"
        "Команды:\n"
        "/register - Регистрация\n"
        "/enter_scores - Ввести баллы\n"
        "/view_scores - Мои баллы"
    )

# Регистрация
@bot.on.private_message(text="/register")
async def register_start(message: Message):
    logger.info(f"ВК Бот: Юзер {message.from_id} начал регистрацию")
    await message.answer("Введите Имя и Фамилию:")
    await bot.state_dispenser.set(message.peer_id, RegisterState.NAME)

@bot.on.private_message(state=RegisterState.NAME)
async def register_process(message: Message):
    logger.info(f"ВК Бот: Юзер {message.from_id} ввел данные для регистрации: {message.text}")
    parts = message.text.split()
    if len(parts) < 2:
        logger.warning(f"ВК Бот: Неверный формат имени от {message.from_id}")
        await message.answer("Нужно ввести Имя и Фамилию.")
        return

    first_name, last_name = parts[0], parts[1]
    vk_id = message.from_id

    async with httpx.AsyncClient() as client:
        payload = {"telegram_id": vk_id, "first_name": first_name, "last_name": last_name}
        try:
            logger.info(f"ВК Бот: Отправка запроса в API для регистрации {vk_id}")
            resp = await client.post(f"{settings.API_BASE_URL}/users/", json=payload)
            if resp.status_code == 200:
                logger.info(f"ВК Бот: Юзер {vk_id} успешно зарегистрирован")
                await message.answer(f"Ученик {first_name} {last_name} зарегистрирован!")
            else:
                logger.error(f"ВК Бот: Ошибка API {resp.status_code} при регистрации {vk_id}")
                await message.answer("Ошибка регистрации.")
        except Exception as e:
            logger.error(f"ВК Бот: Ошибка соединения с API: {e}")
            await message.answer("Ошибка соединения с сервером.")

    await bot.state_dispenser.delete(message.peer_id)

# Ввод баллов
@bot.on.private_message(text="/enter_scores")
async def enter_scores_start(message: Message):
    logger.info(f"ВК Бот: Юзер {message.from_id} начал ввод баллов")
    await message.answer("Напишите название предмета (например: Математика):")
    await bot.state_dispenser.set(message.peer_id, ScoreState.SUBJECT)

@bot.on.private_message(state=ScoreState.SUBJECT)
async def enter_scores_subject(message: Message):
    logger.info(f"ВК Бот: Юзер {message.from_id} выбрал предмет: {message.text}")
    ctx_storage.set(f"{message.peer_id}_subject", message.text)
    await message.answer("Теперь введите балл (число):")
    await bot.state_dispenser.set(message.peer_id, ScoreState.SCORE)

@bot.on.private_message(state=ScoreState.SCORE)
async def enter_scores_value(message: Message):
    if not message.text.isdigit():
        logger.warning(f"ВК Бот: Юзер {message.from_id} ввел не число в баллах: {message.text}")
        await message.answer("Введите число!")
        return

    score = int(message.text)
    subject = ctx_storage.get(f"{message.peer_id}_subject")
    vk_id = message.from_id

    async with httpx.AsyncClient() as client:
        payload = {"telegram_id": vk_id, "subject": subject, "score": score}
        try:
            logger.info(f"ВК Бот: Отправка баллов в API для {vk_id} ({subject}: {score})")
            resp = await client.post(f"{settings.API_BASE_URL}/scores/", json=payload)
            if resp.status_code == 200:
                logger.info(f"ВК Бот: Баллы для {vk_id} сохранены успешно")
                await message.answer(f"Сохранено: {subject} - {score}")
            elif resp.status_code == 404:
                logger.warning(f"ВК Бот: Юзер {vk_id} пытался ввести баллы без регистрации")
                await message.answer("Сначала зарегистрируйтесь! (/register)")
            else:
                logger.error(f"ВК Бот: API вернул код {resp.status_code} при вводе баллов")
        except Exception as e:
            logger.error(f"ВК Бот: Ошибка API при вводе баллов: {e}")

    await bot.state_dispenser.delete(message.peer_id)

# Просмотр
@bot.on.private_message(text="/view_scores")
async def view_scores(message: Message):
    vk_id = message.from_id
    logger.info(f"ВК Бот: Юзер {vk_id} запросил просмотр баллов")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{settings.API_BASE_URL}/scores/{vk_id}")
            if resp.status_code == 200:
                scores = resp.json()
                logger.info(f"ВК Бот: Получено {len(scores)} записей для {vk_id}")
                if not scores:
                    await message.answer("Баллов нет.")
                    return
                text = "\n".join([f"{s['subject']}: {s['score']}" for s in scores])
                await message.answer(f"Ваши баллы:\n{text}")
            else:
                logger.error(f"ВК Бот: API вернул код {resp.status_code} при просмотре баллов")
                await message.answer("Не удалось получить данные.")
        except Exception as e:
            logger.error(f"ВК Бот: Ошибка при просмотре баллов: {e}")
if __name__ == "__main__":
    logger.info("ВК Бот: Запуск бота...")
    bot.run_forever()
