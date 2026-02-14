from aiogram import Bot

from bot.database.repository import ReferralAbuseRepository
from bot.services.admin_notify import notify_admin_abuse_flag

JOIN_SPIKE_WINDOW_MIN = 5
JOIN_SPIKE_THRESHOLD = 8
LEAVE_SPIKE_WINDOW_MIN = 5
LEAVE_SPIKE_THRESHOLD = 5
REJOIN_WINDOW_MIN = 60
REJOIN_THRESHOLD = 3
FLAG_COOLDOWN_MIN = 30


async def inspect_join_event(
    *,
    bot: Bot,
    telegram_id: int,
    referral_link_id: int,
    owner_telegram_id: int | None,
    counted: bool,
) -> None:
    # 1) Резкий всплеск новых join по одной ссылке.
    if counted:
        joins_count = await ReferralAbuseRepository.count_recent_link_actions(
            referral_link_id=referral_link_id,
            action="join",
            window_minutes=JOIN_SPIKE_WINDOW_MIN,
        )
        if joins_count >= JOIN_SPIKE_THRESHOLD:
            details = (
                f"referral_link_id={referral_link_id};"
                f"owner={owner_telegram_id};"
                f"joins_{JOIN_SPIKE_WINDOW_MIN}m={joins_count}"
            )
            created = await ReferralAbuseRepository.create_flag_if_new(
                flag_type="join_spike",
                telegram_id=owner_telegram_id,
                referral_link_id=referral_link_id,
                details=details,
                cooldown_minutes=FLAG_COOLDOWN_MIN,
            )
            if created:
                await notify_admin_abuse_flag(
                    bot,
                    (
                        "🚨 <b>Антиабьюз: всплеск вступлений</b>\n\n"
                        f"Ссылка: <code>{referral_link_id}</code>\n"
                        f"Владелец: <code>{owner_telegram_id}</code>\n"
                        f"Вступлений за {JOIN_SPIKE_WINDOW_MIN} мин: <b>{joins_count}</b>"
                    ),
                )

    # 2) Частые ре-join попытки одного и того же пользователя.
    if not counted:
        rejoins_count = await ReferralAbuseRepository.count_recent_user_rejoins(
            telegram_id=telegram_id,
            window_minutes=REJOIN_WINDOW_MIN,
        )
        if rejoins_count >= REJOIN_THRESHOLD:
            details = (
                f"telegram_id={telegram_id};"
                f"rejoins_{REJOIN_WINDOW_MIN}m={rejoins_count}"
            )
            created = await ReferralAbuseRepository.create_flag_if_new(
                flag_type="frequent_rejoin_attempts",
                telegram_id=telegram_id,
                referral_link_id=referral_link_id,
                details=details,
                cooldown_minutes=FLAG_COOLDOWN_MIN,
            )
            if created:
                await notify_admin_abuse_flag(
                    bot,
                    (
                        "🚨 <b>Антиабьюз: частые повторные входы</b>\n\n"
                        f"Пользователь: <code>{telegram_id}</code>\n"
                        f"Ссылка: <code>{referral_link_id}</code>\n"
                        f"Повторных входов за {REJOIN_WINDOW_MIN} мин: <b>{rejoins_count}</b>"
                    ),
                )


async def inspect_leave_event(
    *,
    bot: Bot,
    telegram_id: int,
    referral_link_id: int,
) -> None:
    # Массовые выходы по одной ссылке за короткий интервал.
    leaves_count = await ReferralAbuseRepository.count_recent_link_actions(
        referral_link_id=referral_link_id,
        action="leave",
        window_minutes=LEAVE_SPIKE_WINDOW_MIN,
    )
    if leaves_count < LEAVE_SPIKE_THRESHOLD:
        return

    details = (
        f"referral_link_id={referral_link_id};"
        f"trigger_telegram_id={telegram_id};"
        f"leaves_{LEAVE_SPIKE_WINDOW_MIN}m={leaves_count}"
    )
    created = await ReferralAbuseRepository.create_flag_if_new(
        flag_type="leave_spike",
        telegram_id=telegram_id,
        referral_link_id=referral_link_id,
        details=details,
        cooldown_minutes=FLAG_COOLDOWN_MIN,
    )
    if created:
        await notify_admin_abuse_flag(
            bot,
            (
                "🚨 <b>Антиабьюз: массовые выходы</b>\n\n"
                f"Ссылка: <code>{referral_link_id}</code>\n"
                f"Выходов за {LEAVE_SPIKE_WINDOW_MIN} мин: <b>{leaves_count}</b>"
            ),
        )
