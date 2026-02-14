from unittest.mock import AsyncMock

import pytest

from bot.services import referral_abuse


@pytest.mark.asyncio
async def test_join_spike_sends_admin_report(monkeypatch):
    monkeypatch.setattr(
        referral_abuse.ReferralAbuseRepository,
        "count_recent_link_actions",
        staticmethod(AsyncMock(return_value=referral_abuse.JOIN_SPIKE_THRESHOLD)),
    )
    monkeypatch.setattr(
        referral_abuse.ReferralAbuseRepository,
        "create_flag_if_new",
        staticmethod(AsyncMock(return_value=True)),
    )
    notify = AsyncMock()
    monkeypatch.setattr(referral_abuse, "notify_admin_abuse_flag", notify)

    await referral_abuse.inspect_join_event(
        bot=object(),
        telegram_id=777,
        referral_link_id=10,
        owner_telegram_id=111,
        counted=True,
    )

    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejoin_threshold_sends_admin_report(monkeypatch):
    monkeypatch.setattr(
        referral_abuse.ReferralAbuseRepository,
        "count_recent_user_rejoins",
        staticmethod(AsyncMock(return_value=referral_abuse.REJOIN_THRESHOLD)),
    )
    monkeypatch.setattr(
        referral_abuse.ReferralAbuseRepository,
        "create_flag_if_new",
        staticmethod(AsyncMock(return_value=True)),
    )
    notify = AsyncMock()
    monkeypatch.setattr(referral_abuse, "notify_admin_abuse_flag", notify)

    await referral_abuse.inspect_join_event(
        bot=object(),
        telegram_id=777,
        referral_link_id=10,
        owner_telegram_id=111,
        counted=False,
    )

    notify.assert_awaited_once()

