import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import leaderboard as leaderboard_handler
from bot.handlers import start as start_handler
from bot.services.leaderboard_cache import invalidate_leaderboard_cache


def _build_callback(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(
            edit_text=AsyncMock(),
            answer=AsyncMock(),
        ),
        answer=AsyncMock(),
        data="leaderboard",
    )


def _build_state() -> SimpleNamespace:
    return SimpleNamespace(clear=AsyncMock())


@pytest.mark.asyncio
async def test_back_to_menu_handles_150_concurrent_clicks(monkeypatch):
    send_welcome_mock = AsyncMock()
    monkeypatch.setattr(start_handler, "send_welcome", send_welcome_mock)

    users = 150
    callbacks = [_build_callback(user_id=1000 + i) for i in range(users)]
    states = [_build_state() for _ in range(users)]

    await asyncio.gather(
        *(
            start_handler.back_to_menu(callback=callbacks[i], state=states[i])
            for i in range(users)
        )
    )

    assert send_welcome_mock.await_count == users
    assert all(state.clear.await_count == 1 for state in states)
    assert all(callback.answer.await_count == 1 for callback in callbacks)


@pytest.mark.asyncio
async def test_cancel_action_handles_150_concurrent_clicks(monkeypatch):
    send_welcome_mock = AsyncMock()
    monkeypatch.setattr(start_handler, "send_welcome", send_welcome_mock)

    users = 150
    callbacks = [_build_callback(user_id=2000 + i) for i in range(users)]
    states = [_build_state() for _ in range(users)]

    await asyncio.gather(
        *(
            start_handler.cancel_action(callback=callbacks[i], state=states[i])
            for i in range(users)
        )
    )

    assert send_welcome_mock.await_count == users
    assert all(state.clear.await_count == 1 for state in states)
    assert all(callback.answer.await_count == 1 for callback in callbacks)


@pytest.mark.asyncio
async def test_leaderboard_handles_150_concurrent_clicks(monkeypatch):
    invalidate_leaderboard_cache()

    rows = [
        (SimpleNamespace(username="u1", first_name="User1", telegram_id=10), 5),
        (SimpleNamespace(username="u2", first_name="User2", telegram_id=20), 3),
    ]
    query_mock = AsyncMock(return_value=rows)
    monkeypatch.setattr(
        leaderboard_handler.ReferralStatsRepository,
        "get_top_referrers_by_period",
        staticmethod(query_mock),
    )

    users = 150
    callbacks = [_build_callback(user_id=3000 + i) for i in range(users)]

    await asyncio.gather(
        *(leaderboard_handler.show_leaderboard_default(callback=cb) for cb in callbacks)
    )

    # Запрос в БД должен быть вызван хотя бы один раз; дальше ответы могли уйти из кеша.
    assert query_mock.await_count >= 1
    assert all(callback.answer.await_count == 1 for callback in callbacks)
    assert all(callback.message.edit_text.await_count == 1 for callback in callbacks)
