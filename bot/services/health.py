from aiohttp import web
from loguru import logger

from bot.config import settings


async def handle_health(request: web.Request) -> web.Response:
    """Простая проверка здоровья сервиса."""
    # В будущем можно добавить проверку подключения к БД
    return web.Response(text="OK", status=200)


async def start_healthcheck() -> web.AppRunner:
    """Запустить HTTP сервер для Healthcheck."""
    app = web.Application()
    app.add_routes([web.get("/health", handle_health)])
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", port=settings.port)
    await site.start()
    
    logger.info(f"Healthcheck server started on port {settings.port}")
    return runner


async def stop_healthcheck(runner: web.AppRunner) -> None:
    """Остановить HTTP сервер."""
    if runner:
        await runner.cleanup()
        logger.info("Healthcheck server stopped")
