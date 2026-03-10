import asyncio


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from bot.config import settings
from bot.handlers import admin, admin_contact, advertising, leaderboard, referral, start
from bot.middlewares.rate_limit import rate_limiter
from bot.services.broadcast_worker import BroadcastWorker
from bot.services.health import start_healthcheck, stop_healthcheck



async def main() -> None:
    """Entry point for bot process."""
    logger.info("Bot initialization...")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.message.middleware(rate_limiter)
    dp.callback_query.middleware(rate_limiter)

    # Routers
    dp.include_router(start.router)
    dp.include_router(referral.router)
    dp.include_router(advertising.router)
    dp.include_router(admin_contact.router)
    dp.include_router(leaderboard.router)
    dp.include_router(admin.router)

    # Startup / Shutdown logic
    async def on_startup(dispatcher: Dispatcher) -> None:
        logger.info("Starting up...")
        
        # 1. Start BroadcastWorker
        logger.info("Starting broadcast worker...")
        worker = BroadcastWorker(
            bot=bot,
            poll_interval_seconds=settings.broadcast_worker_poll_seconds,
        )
        await worker.start()
        # Сохраняем worker в workflow_data, чтобы достать при shutdown
        dispatcher["broadcast_worker"] = worker
        
        # 2. Start Healthcheck Server
        try:
            runner = await start_healthcheck()
            dispatcher["healthcheck_runner"] = runner
        except Exception as e:
            logger.error(f"Healthcheck server failed to start: {e}")

        logger.info("Bot started")
        logger.info(f"Configured admins: {len(settings.admin_ids)}")

    async def on_shutdown(dispatcher: Dispatcher) -> None:
        logger.info("Bot shutdown...")
        
        # 1. Stop components
        worker: BroadcastWorker | None = dispatcher.get("broadcast_worker")
        if worker:
            await worker.stop()

        health_runner = dispatcher.get("healthcheck_runner")
        if health_runner:
            await stop_healthcheck(health_runner)
        
        # 2. Close resources
        await storage.close()
        await bot.session.close()
        logger.info("Bot stopped")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # 1. Сбрасываем вебхук перед запуском polling
    # Это критично, если ранее использовались Edge Functions или другой режим
    logger.info("Deleteting any existing webhooks...")
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.exception(f"Critical error during polling: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by signal")
