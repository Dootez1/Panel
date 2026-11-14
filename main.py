import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import start, survey, worker, admin, admin_private
from middlewares import SecurityBanMiddleware, AntiFloodMiddleware, SubscriptionMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def main():
    if not BOT_TOKEN or "AAG-EyCuLRcabnJvC5sV8SBBXf14WLr44Uw" not in BOT_TOKEN:
        logging.error("BOT_TOKEN is not set properly in config/.env!")

    await init_db()
    logging.info("База данных SQLite успешно инициализирована.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Глобальные защитные middleware: блокировка забаненных, защита от флуда и обязательная подписка
    dp.message.outer_middleware(SecurityBanMiddleware())
    dp.callback_query.outer_middleware(SecurityBanMiddleware())
    dp.message.outer_middleware(AntiFloodMiddleware(rate_limit=0.4))
    dp.callback_query.outer_middleware(AntiFloodMiddleware(rate_limit=0.4))
    dp.message.outer_middleware(SubscriptionMiddleware())
    dp.callback_query.outer_middleware(SubscriptionMiddleware())

    # Регистрация роутеров aiogram:
    # 1. admin_private.router — полнофункциональная админ-панель в Telegram
    # 2. admin.router — модерация и команды в группе администрации
    # 3. start.router — регистрация и главное меню
    # 4. survey.router — анкетирование кандидатов
    # 5. worker.router — функционал воркера (отчеты профитов, заявки на вывод, инфо)
    dp.include_router(admin_private.router)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(survey.router)
    dp.include_router(worker.router)

    logging.info("🤖 Бот Haster TEAM запускается в режиме Polling...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
