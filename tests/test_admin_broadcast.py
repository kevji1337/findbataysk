from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import admin as admin_handler
from bot.states.admin_broadcast import AdminBroadcastStates


@pytest.mark.asyncio
async def test_admin_broadcast_send_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: False)

    state = SimpleNamespace(
        clear=AsyncMock(),
        get_data=AsyncMock(return_value={"broadcast_started_at": datetime.now(UTC).replace(tzinfo=None).isoformat()}),
    )

    answer = AsyncMock()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=111),
        chat=SimpleNamespace(id=111, type="private"),
        message_id=10,
        answer=answer,
    )

    await admin_handler.admin_broadcast_send(message=message, state=state, bot=object())

    state.clear.assert_awaited_once()
    answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_broadcast_send_saves_draft_and_requests_confirmation(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: True)

    state = SimpleNamespace(
        clear=AsyncMock(),
        get_data=AsyncMock(
            return_value={
                "broadcast_started_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            }
        ),
        update_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    answer = AsyncMock()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=777),
        chat=SimpleNamespace(id=777, type="private"),
        message_id=77,
        answer=answer,
    )

    await admin_handler.admin_broadcast_send(message=message, state=state, bot=object())

    state.clear.assert_not_called()
    state.update_data.assert_awaited_once()
    state.set_state.assert_awaited_once_with(AdminBroadcastStates.waiting_confirmation)
    answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_broadcast_confirm_queues_job_and_logs(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: True)

    async def _get_ids() -> list[int]:
        return [1001, 1002, 1003]

    monkeypatch.setattr(
        admin_handler.UserRepository,
        "get_broadcast_telegram_ids",
        staticmethod(_get_ids),
    )

    create_job = AsyncMock(
        return_value=SimpleNamespace(
            id=42,
            created_by_admin_id=777,
            total_users=3,
        )
    )
    monkeypatch.setattr(
        admin_handler.BroadcastJobRepository,
        "create",
        staticmethod(create_job),
    )

    log_create = AsyncMock()
    monkeypatch.setattr(
        admin_handler.AdminActionLogRepository,
        "create",
        staticmethod(log_create),
    )

    state = SimpleNamespace(
        clear=AsyncMock(),
        get_data=AsyncMock(
            return_value={
                "broadcast_started_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                "broadcast_source_chat_id": 777,
                "broadcast_source_message_id": 77,
            }
        ),
    )

    callback = SimpleNamespace(
        data="admin_broadcast_confirm",
        from_user=SimpleNamespace(id=777),
        message=SimpleNamespace(
            edit_text=AsyncMock(),
            answer=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await admin_handler.admin_broadcast_confirm(callback=callback, state=state)

    create_job.assert_awaited_once()
    kwargs = create_job.await_args.kwargs
    assert kwargs["recipient_ids"] == [1001, 1002, 1003]

    log_create.assert_awaited_once()
    state.clear.assert_awaited_once()
    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
