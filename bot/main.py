import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot.config import BOT_TOKEN
from bot.handlers import start, registration, questions, admin
from db.database import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()


    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(questions.router)
    
    print("Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
