from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.config import settings
from bot.database.repository import (
    AdminActionLogRepository,
    AdvertisingRepository,
    UserRepository,
)
from bot.keyboards.inline import (
    get_ad_criteria_keyboard,
    get_back_to_menu_keyboard,
    get_cancel_keyboard,
)
from bot.middlewares.rate_limit import rate_limiter
from bot.services.admin_notify import notify_admin_new_ad_request, notify_user_ad_decision
from bot.services.referral import validate_channel_link
from bot.states.advertising import AdvertisingStates


router = Router(name="advertising")


@router.callback_query(lambda c: c.data == "advertising")
async def show_ad_criteria(callback: types.CallbackQuery) -> None:
    """Показать критерии для рекламы."""
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        text=settings.ad_criteria,
        reply_markup=get_ad_criteria_keyboard(),
    )
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.callback_query(lambda c: c.data == "ad_criteria_confirmed")
async def ad_criteria_confirmed(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    """Пользователь подтвердил соответствие критериям."""
    await state.set_state(AdvertisingStates.waiting_channel_link)

    _prompt_text = (
        "📎 <b>Отправьте ссылку на Ваш ТГК для проверки администрацией</b>\n\n"
        "Поддерживаемые форматы:\n"
        "• https://t.me/your_channel\n"
        "• @your_channel\n"
        "• Приватные ссылки t.me/+..."
    )

    try:
        await callback.message.edit_text(
            text=_prompt_text,
            reply_markup=get_cancel_keyboard(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text=_prompt_text,
            reply_markup=get_cancel_keyboard(),
        )

    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.message(AdvertisingStates.waiting_channel_link, F.text)
async def process_channel_link(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    """Обработка ссылки на канал от пользователя."""
    channel_link = message.text.strip()

    if not validate_channel_link(channel_link):
        await message.answer(
            text=(
                "❌ <b>Неверный формат ссылки!</b>\n\n"
                "Пожалуйста, отправьте корректную ссылку на Telegram канал.\n\n"
                "Поддерживаемые форматы:\n"
                "• https://t.me/your_channel\n"
                "• @your_channel\n"
                "• Приватные ссылки t.me/+..."
            ),
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Отдельный лимит именно на создание рекламных заявок.
    allowed, seconds_left = rate_limiter.check_rate_limit(
        user_id=message.from_user.id,
        action_type="ad_request",
    )
    if not allowed:
        await message.answer(
            text=(
                "⏳ <b>Слишком много заявок.</b>\n\n"
                f"Повторите попытку через {seconds_left} сек."
            ),
            reply_markup=get_back_to_menu_keyboard(),
        )
        await state.clear()
        return

    rate_limiter.record_action(
        user_id=message.from_user.id,
        action_type="ad_request",
    )

    user = await UserRepository.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    request = await AdvertisingRepository.create(
        user_id=user.id,
        channel_link=channel_link,
    )

    await notify_admin_new_ad_request(
        bot=bot,
        user_id=message.from_user.id,
        username=message.from_user.username,
        channel_link=channel_link,
        request_id=request.id,
    )

    await state.clear()

    await message.answer(
        text=(
            "✅ <b>Ваша заявка отправлена на проверку!</b>\n\n"
            "Администрация рассмотрит её в ближайшее время. "
            "Вы получите уведомление о решении."
        ),
        reply_markup=get_back_to_menu_keyboard(),
    )

    logger.info(f"Новая заявка на рекламу от пользователя {message.from_user.id}")


# ── Общая логика одобрения/отклонения заявки ──


async def _handle_ad_decision(
    callback: types.CallbackQuery,
    bot: Bot,
    *,
    approved: bool,
) -> None:
    """Общая логика одобрения/отклонения заявки на рекламу."""
    if not settings.is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    try:
        _, request_id_raw = callback.data.split(":")
        request_id = int(request_id_raw)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    request = await AdvertisingRepository.get_by_id(request_id)
    if not request:
        await callback.answer("⚠️ Заявка не найдена", show_alert=True)
        return

    request_user = await UserRepository.get_by_id(request.user_id)
    if not request_user:
        await callback.answer("⚠️ Пользователь заявки не найден", show_alert=True)
        return

    new_status = "approved" if approved else "rejected"
    updated = await AdvertisingRepository.update_status(request_id, new_status)
    if not updated:
        await callback.answer("⚠️ Заявка уже обработана", show_alert=True)
        return

    await notify_user_ad_decision(bot, request_user.telegram_id, approved=approved)

    action_type = "ad_approve" if approved else "ad_reject"
    await AdminActionLogRepository.create(
        admin_telegram_id=callback.from_user.id,
        action_type=action_type,
        target_type="advertising_request",
        target_id=request_id,
        details=f"user_id={request.user_id}",
    )

    suffix = "✅ <b>Заявка одобрена</b>" if approved else "❌ <b>Заявка отклонена</b>"
    label = "Заявка одобрена" if approved else "Заявка отклонена"

    await callback.message.edit_text(
        text=callback.message.text + f"\n\n{suffix}",
    )
    try:
        await callback.answer(label)
    except TelegramBadRequest:
        pass

    logger.info(f"Заявка {request_id} {label.lower()}")


@router.callback_query(lambda c: c.data.startswith("ad_approve:"))
async def approve_ad_request(callback: types.CallbackQuery, bot: Bot) -> None:
    """Админ одобряет заявку на рекламу."""
    await _handle_ad_decision(callback, bot, approved=True)


@router.callback_query(lambda c: c.data.startswith("ad_reject:"))
async def reject_ad_request(callback: types.CallbackQuery, bot: Bot) -> None:
    """Админ отклоняет заявку на рекламу."""
    await _handle_ad_decision(callback, bot, approved=False)
