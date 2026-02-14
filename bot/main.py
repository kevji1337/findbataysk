import asyncio
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from bot.config import settings
from bot.handlers import admin, admin_contact, advertising, leaderboard, referral, start
from bot.middlewares.rate_limit import rate_limiter
from bot.services.broadcast_worker import BroadcastWorker


async def main() -> None:
    """Entry point for bot process."""
    logger.info("Bot initialization...")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    dp.message.middleware(rate_limiter)
    dp.callback_query.middleware(rate_limiter)

    dp.include_router(start.router)
    dp.include_router(referral.router)
    dp.include_router(advertising.router)
    dp.include_router(admin_contact.router)
    dp.include_router(leaderboard.router)
    dp.include_router(admin.router)

    broadcast_worker = BroadcastWorker(
        bot=bot,
        poll_interval_seconds=settings.broadcast_worker_poll_seconds,
    )
    await broadcast_worker.start()

    async def on_shutdown() -> None:
        logger.info("Bot shutdown...")
        await broadcast_worker.stop()
        await storage.close()
        await bot.session.close()
        logger.info("Bot stopped")

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(on_shutdown()))
        except NotImplementedError:
            pass

    logger.info("Bot started")
    logger.info(f"Configured admins: {len(settings.admin_ids)}")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        pass
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by Ctrl+C")
