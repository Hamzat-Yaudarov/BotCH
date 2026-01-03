import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db, close_db
from handlers import commands, callbacks

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Include routers
dp.include_router(commands.router)
dp.include_router(callbacks.router)


async def main():
    """Start the bot"""
    # Initialize database
    await init_db()

    try:
        await dp.start_polling(bot)
    finally:
        # Close database connection pool
        await close_db()


if __name__ == '__main__':
    asyncio.run(main())
