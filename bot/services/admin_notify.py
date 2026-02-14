from aiogram import Bot
from loguru import logger

from bot.config import settings


async def _notify_all_admins(bot: Bot, text: str, reply_markup=None) -> None:
    """Отправить сообщение всем админам."""
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def notify_admin_new_referral_link(
    bot: Bot, user_id: int, username: str | None, invite_link: str
) -> None:
    """Уведомить админов о создании новой реферальной ссылки."""
    user_mention = f"@{username}" if username else f"ID: {user_id}"
    text = (
        f"🔗 <b>Создана новая реферальная ссылка</b>\n\n"
        f"👤 Пользователь: {user_mention}\n"
        f"🔗 Ссылка: {invite_link}"
    )
    await _notify_all_admins(bot, text)


async def notify_admin_new_ad_request(
    bot: Bot,
    user_id: int,
    username: str | None,
    channel_link: str,
    request_id: int,
) -> None:
    """Уведомить админов о новой заявке на рекламу."""
    from bot.keyboards.inline import get_ad_review_keyboard

    user_mention = f"@{username}" if username else f"ID: {user_id}"
    text = (
        f"📢 <b>Новая заявка на рекламу</b>\n\n"
        f"👤 Пользователь: {user_mention}\n"
        f"📎 Канал: {channel_link}\n"
        f"🆔 ID заявки: {request_id}"
    )
    keyboard = get_ad_review_keyboard(request_id)
    await _notify_all_admins(bot, text, reply_markup=keyboard)


async def notify_user_new_referral(bot: Bot, user_telegram_id: int) -> None:
    """Уведомить пользователя о новом переходе по его ссылке."""
    text = "🎉 <b>По вашей ссылке зашёл новый человек!</b>"
    try:
        await bot.send_message(chat_id=user_telegram_id, text=text)
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_telegram_id}: {e}")


async def notify_user_ad_decision(
    bot: Bot, user_telegram_id: int, approved: bool
) -> None:
    """Уведомить пользователя о решении по заявке на рекламу."""
    if approved:
        text = (
            "✅ <b>Ваша заявка на рекламу одобрена!</b>\n\n"
            "Администрация свяжется с вами в ближайшее время для обсуждения деталей."
        )
    else:
        text = (
            "❌ <b>Ваша заявка на рекламу отклонена.</b>\n\n"
            "К сожалению, ваш канал не соответствует нашим критериям. "
            "Вы можете подать заявку повторно, когда канал будет соответствовать требованиям."
        )
    try:
        await bot.send_message(chat_id=user_telegram_id, text=text)
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_telegram_id}: {e}")



async def notify_admin_abuse_flag(bot: Bot, text: str) -> None:
    """Уведомить админов о подозрительной реферальной активности."""
    await _notify_all_admins(bot, text)
