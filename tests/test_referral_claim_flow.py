from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import referral as referral_handler


@pytest.mark.asyncio
async def test_claim_referral_gift_rolls_back_when_admin_unreachable(monkeypatch):
    monkeypatch.setattr(referral_handler.settings, "admin_ids", [11, 22], raising=False)

    monkeypatch.setattr(
        referral_handler.UserRepository,
        "get_by_telegram_id",
        staticmethod(AsyncMock(return_value=SimpleNamespace(id=7))),
    )
    monkeypatch.setattr(
        referral_handler.ReferralRepository,
        "get_by_user_id",
        staticmethod(
            AsyncMock(
                return_value=SimpleNamespace(
                    id=99,
                    referral_count=12,
                    gifts_claimed=0,
                )
            )
        ),
    )
    monkeypatch.setattr(
        referral_handler.ReferralRepository,
        "claim_available_gifts",
        staticmethod(AsyncMock(return_value=2)),
    )
    release_claimed = AsyncMock()
    monkeypatch.setattr(
        referral_handler.ReferralRepository,
        "release_claimed_gifts",
        staticmethod(release_claimed),
    )

    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=555, username="tester"),
        message=SimpleNamespace(edit_text=AsyncMock(), answer=AsyncMock()),
        answer=AsyncMock(),
    )
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError("down")))

    await referral_handler.claim_referral_gift(callback=callback, bot=bot)

    release_claimed.assert_awaited_once_with(99, 2)
    callback.answer.assert_awaited_once()
