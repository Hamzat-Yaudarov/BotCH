import asyncio
import logging
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# Загружаем переменные окружения из .env файла
load_dotenv()

from config import BOT_TOKEN, LOG_LEVEL
from database import db
from handlers import get_routers

# Попытка импортировать DefaultBotProperties (для новых версий aiogram)
try:
    from aiogram.client.default import DefaultBotProperties
    HAS_DEFAULT_BOT_PROPERTIES = True
except ImportError:
    HAS_DEFAULT_BOT_PROPERTIES = False


# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска бота"""

    # Инициализируем БД
    logger.info("📦 Инициализация базы данных...")
    from config import DATABASE_URL
    logger.info(f"DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "DATABASE_URL not set!")
    try:
        await db.initialize()
        logger.info("✅ База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Создаём бота
    logger.info("🤖 Инициализация бота...")
    if HAS_DEFAULT_BOT_PROPERTIES:
        from aiogram.client.default import DefaultBotProperties
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    else:
        bot = Bot(token=BOT_TOKEN)

    # Создаём диспетчер со storage в памяти (для FSM)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем все маршруты
    for router in get_routers():
        dp.include_router(router)

    logger.info("✅ Бот инициализирован, начинаем polling...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка polling: {e}")
    finally:
        await bot.session.close()
        await db.close()
        logger.info("✅ Бот остановлен")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
        sys.exit(0)
