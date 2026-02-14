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
    # Удаляем предыдущее сообщение (может быть фото)
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
    
    try:
        await callback.message.edit_text(
            text=(
                "📎 <b>Отправьте ссылку на Ваш ТГК для проверки администрацией</b>\n\n"
                "Поддерживаемые форматы:\n"
                "• https://t.me/your_channel\n"
                "• @your_channel\n"
                "• Приватные ссылки t.me/+..."
            ),
            reply_markup=get_cancel_keyboard(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text=(
                "📎 <b>Отправьте ссылку на Ваш ТГК для проверки администрацией</b>\n\n"
                "Поддерживаемые форматы:\n"
                "• https://t.me/your_channel\n"
                "• @your_channel\n"
                "• Приватные ссылки t.me/+..."
            ),
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

    # Валидация ссылки
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

    # Получаем пользователя
    user = await UserRepository.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    # Создаём заявку
    request = await AdvertisingRepository.create(
        user_id=user.id,
        channel_link=channel_link,
    )

    # Уведомляем админа
    await notify_admin_new_ad_request(
        bot=bot,
        user_id=message.from_user.id,
        username=message.from_user.username,
        channel_link=channel_link,
        request_id=request.id,
    )

    # Сбрасываем состояние
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


@router.callback_query(lambda c: c.data.startswith("ad_approve:"))
async def approve_ad_request(callback: types.CallbackQuery, bot: Bot) -> None:
    """Админ одобряет заявку на рекламу."""
    # ПРОВЕРКА АВТОРИЗАЦИИ
    if not settings.is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    try:
        _, request_id = callback.data.split(":")
        request_id = int(request_id)
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

    # Обновляем статус заявки (только если она ещё pending)
    updated = await AdvertisingRepository.update_status(request_id, "approved")
    if not updated:
        await callback.answer("⚠️ Заявка уже обработана", show_alert=True)
        return

    # Уведомляем пользователя
    await notify_user_ad_decision(bot, request_user.telegram_id, approved=True)
    await AdminActionLogRepository.create(
        admin_telegram_id=callback.from_user.id,
        action_type="ad_approve",
        target_type="advertising_request",
        target_id=request_id,
        details=f"user_id={request.user_id}",
    )

    await callback.message.edit_text(
        text=callback.message.text + "\n\n✅ <b>Заявка одобрена</b>",
    )
    try:
        await callback.answer("Заявка одобрена")
    except TelegramBadRequest:
        pass

    logger.info(f"Заявка {request_id} одобрена")


@router.callback_query(lambda c: c.data.startswith("ad_reject:"))
async def reject_ad_request(callback: types.CallbackQuery, bot: Bot) -> None:
    """Админ отклоняет заявку на рекламу."""
    # ПРОВЕРКА АВТОРИЗАЦИИ
    if not settings.is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    try:
        _, request_id = callback.data.split(":")
        request_id = int(request_id)
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

    # Обновляем статус заявки (только если она ещё pending)
    updated = await AdvertisingRepository.update_status(request_id, "rejected")
    if not updated:
        await callback.answer("⚠️ Заявка уже обработана", show_alert=True)
        return

    # Уведомляем пользователя
    await notify_user_ad_decision(bot, request_user.telegram_id, approved=False)
    await AdminActionLogRepository.create(
        admin_telegram_id=callback.from_user.id,
        action_type="ad_reject",
        target_type="advertising_request",
        target_id=request_id,
        details=f"user_id={request.user_id}",
    )

    await callback.message.edit_text(
        text=callback.message.text + "\n\n❌ <b>Заявка отклонена</b>",
    )
    try:
        await callback.answer("Заявка отклонена")
    except TelegramBadRequest:
        pass

    logger.info(f"Заявка {request_id} отклонена")
