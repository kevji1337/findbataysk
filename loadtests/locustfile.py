import asyncio
import random
import threading
import time
from types import SimpleNamespace

from locust import User, between, events, task

from bot.handlers import leaderboard as leaderboard_handler
from bot.handlers import start as start_handler
from bot.services.leaderboard_cache import invalidate_leaderboard_cache


def _build_callback(user_id: int, data: str) -> SimpleNamespace:
    async def _noop(*args, **kwargs) -> None:
        return None

    message = SimpleNamespace(
        edit_text=_noop,
        answer=_noop,
    )
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        message=message,
        data=data,
        answer=_noop,
    )


def _build_state() -> SimpleNamespace:
    async def _clear() -> None:
        return None

    return SimpleNamespace(clear=_clear)


class AsyncBridge:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._ready.clear()

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._ready.set()
            loop.run_forever()
            loop.close()

        self._thread = threading.Thread(target=_runner, name="locust-async-bridge", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def run(self, coro):
        if not self._loop:
            raise RuntimeError("async bridge loop is not started")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=5)

    def stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None
        self._ready.clear()


_ASYNC_BRIDGE = AsyncBridge()


@events.test_start.add_listener
def _on_test_start(environment, **kwargs) -> None:
    _ = (environment, kwargs)
    _ASYNC_BRIDGE.start()


@events.test_stop.add_listener
def _on_test_stop(environment, **kwargs) -> None:
    _ = (environment, kwargs)
    _ASYNC_BRIDGE.stop()


def _run_async(request_name: str, coro) -> None:
    started = time.perf_counter()
    try:
        _ASYNC_BRIDGE.run(coro)
    except Exception as exc:
        try:
            coro.close()
        except Exception:
            pass
        elapsed_ms = (time.perf_counter() - started) * 1000
        events.request.fire(
            request_type="bot_menu",
            name=request_name,
            response_time=elapsed_ms,
            response_length=0,
            exception=exc,
            context={},
        )
        return

    elapsed_ms = (time.perf_counter() - started) * 1000
    events.request.fire(
        request_type="bot_menu",
        name=request_name,
        response_time=elapsed_ms,
        response_length=0,
        exception=None,
        context={},
    )


def _patch_dependencies() -> None:
    if getattr(_patch_dependencies, "_done", False):
        return

    async def _fake_send_welcome(target, *, as_new_message: bool = False) -> None:
        _ = (target, as_new_message)
        return None

    async def _fake_top_referrers(period: str = "all", limit: int = 10):
        _ = (period, limit)
        return [
            (SimpleNamespace(username="u1", first_name="User1", telegram_id=1001), 12),
            (SimpleNamespace(username="u2", first_name="User2", telegram_id=1002), 8),
        ]

    start_handler.send_welcome = _fake_send_welcome
    leaderboard_handler.ReferralStatsRepository.get_top_referrers_by_period = staticmethod(
        _fake_top_referrers
    )
    invalidate_leaderboard_cache()
    _patch_dependencies._done = True


class BotMenuUser(User):
    wait_time = between(0.01, 0.2)

    def on_start(self) -> None:
        _patch_dependencies()
        self.user_id_base = random.randint(10_000, 999_999)

    @task(5)
    def back_to_menu(self) -> None:
        callback = _build_callback(self.user_id_base + random.randint(1, 100_000), "back_to_menu")
        state = _build_state()
        _run_async("back_to_menu", start_handler.back_to_menu(callback=callback, state=state))

    @task(3)
    def cancel_action(self) -> None:
        callback = _build_callback(
            self.user_id_base + random.randint(1, 100_000),
            "cancel_action",
        )
        state = _build_state()
        _run_async("cancel_action", start_handler.cancel_action(callback=callback, state=state))

    @task(2)
    def leaderboard(self) -> None:
        callback = _build_callback(
            self.user_id_base + random.randint(1, 100_000),
            "leaderboard",
        )
        _run_async("leaderboard", leaderboard_handler.show_leaderboard_default(callback=callback))
