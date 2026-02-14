from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import advertising as advertising_handler


@pytest.mark.asyncio
async def test_approve_ad_request_uses_user_from_db(monkeypatch):
    monkeypatch.setattr(type(advertising_handler.settings), "is_admin", lambda _self, _uid: True)

    request = SimpleNamespace(id=5, user_id=77)
    request_user = SimpleNamespace(id=77, telegram_id=999001)

    monkeypatch.setattr(
        advertising_handler.AdvertisingRepository,
        "get_by_id",
        staticmethod(AsyncMock(return_value=request)),
    )
    monkeypatch.setattr(
        advertising_handler.UserRepository,
        "get_by_id",
        staticmethod(AsyncMock(return_value=request_user)),
    )
    monkeypatch.setattr(
        advertising_handler.AdvertisingRepository,
        "update_status",
        staticmethod(AsyncMock(return_value=True)),
    )

    notify = AsyncMock()
    monkeypatch.setattr(advertising_handler, "notify_user_ad_decision", notify)
    log_create = AsyncMock()
    monkeypatch.setattr(
        advertising_handler.AdminActionLogRepository,
        "create",
        staticmethod(log_create),
    )

    callback = SimpleNamespace(
        data="ad_approve:5",
        from_user=SimpleNamespace(id=12345),
        message=SimpleNamespace(text="req", edit_text=AsyncMock()),
        answer=AsyncMock(),
    )

    bot = object()
    await advertising_handler.approve_ad_request(callback=callback, bot=bot)

    notify.assert_awaited_once_with(bot, request_user.telegram_id, approved=True)
    log_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_ad_request_uses_user_from_db(monkeypatch):
    monkeypatch.setattr(type(advertising_handler.settings), "is_admin", lambda _self, _uid: True)

    request = SimpleNamespace(id=8, user_id=88)
    request_user = SimpleNamespace(id=88, telegram_id=999002)

    monkeypatch.setattr(
        advertising_handler.AdvertisingRepository,
        "get_by_id",
        staticmethod(AsyncMock(return_value=request)),
    )
    monkeypatch.setattr(
        advertising_handler.UserRepository,
        "get_by_id",
        staticmethod(AsyncMock(return_value=request_user)),
    )
    monkeypatch.setattr(
        advertising_handler.AdvertisingRepository,
        "update_status",
        staticmethod(AsyncMock(return_value=True)),
    )

    notify = AsyncMock()
    monkeypatch.setattr(advertising_handler, "notify_user_ad_decision", notify)
    log_create = AsyncMock()
    monkeypatch.setattr(
        advertising_handler.AdminActionLogRepository,
        "create",
        staticmethod(log_create),
    )

    callback = SimpleNamespace(
        data="ad_reject:8",
        from_user=SimpleNamespace(id=12345),
        message=SimpleNamespace(text="req", edit_text=AsyncMock()),
        answer=AsyncMock(),
    )

    bot = object()
    await advertising_handler.reject_ad_request(callback=callback, bot=bot)

    notify.assert_awaited_once_with(bot, request_user.telegram_id, approved=False)
    log_create.assert_awaited_once()
