from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMemberUpdated
from loguru import logger

from bot.config import settings
from bot.core.constants import REFERRALS_PER_GIFT
from bot.core.referral_service import calculate_gift_stats, get_gift_word
from bot.database.repository import ReferralRepository, UserRepository
from bot.keyboards.inline import get_back_to_menu_keyboard
from bot.services.admin_notify import notify_admin_new_referral_link, notify_user_new_referral
from bot.services.referral_abuse import inspect_join_event, inspect_leave_event
from bot.services.referral_events import handle_referral_join, handle_referral_leave


router = Router(name="referral")


@router.callback_query(lambda c: c.data == "referral_program")
async def referral_program(callback: types.CallbackQuery, bot: Bot) -> None:
    """Обработчик кнопки 'Подарок за реф программу'."""
    user = await UserRepository.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    
    # Удаляем предыдущее сообщение (может быть фото)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # Проверяем, есть ли уже ссылка у пользователя
    existing_link = await ReferralRepository.get_by_user_id(user.id)

    if existing_link:
        # Используем сервис для расчёта статистики подарков
        stats = calculate_gift_stats(
            referral_count=existing_link.referral_count,
            gifts_claimed=existing_link.gifts_claimed,
        )
        
        # Формируем текст статуса
        if stats.can_claim:
            status_text = f"✅ Доступно подарков: <b>{stats.available}</b> 🧸"
        else:
            status_text = f"⏳ До следующего подарка: <b>{stats.until_next}</b> переходов"
        
        # Отправляем существующую ссылку
        from bot.keyboards.inline import get_referral_keyboard
        from bot.core.constants import REFERRALS_PER_GIFT
        await callback.message.answer(
            text=(
                f"🔗 <b>Ваша реферальная ссылка:</b>\n\n"
                f"{existing_link.invite_link}\n\n"
                f"📊 Переходов по ссылке: <b>{existing_link.referral_count}</b>\n"
                f"🧸 Получено подарков: <b>{stats.already_claimed}</b>\n\n"
                f"🎁 <b>Награды:</b>\n"
                f"• Каждые {REFERRALS_PER_GIFT} переходов = 🧸 Мишка\n\n"
                f"{status_text}"
            ),
            reply_markup=get_referral_keyboard(stats.can_claim),
        )
    else:
        try:
            # Создаём новую пригласительную ссылку
            invite = await bot.create_chat_invite_link(
                chat_id=settings.channel_id,
                name=f"ref_{callback.from_user.id}",
                creates_join_request=False,
            )

            # Сохраняем в БД
            await ReferralRepository.create(
                user_id=user.id,
                invite_link=invite.invite_link,
            )

            # Уведомляем админа
            await notify_admin_new_referral_link(
                bot=bot,
                user_id=callback.from_user.id,
                username=callback.from_user.username,
                invite_link=invite.invite_link,
            )

            await callback.message.answer(
                text=(
                    f"🎉 <b>Ваша персональная реферальная ссылка создана!</b>\n\n"
                    f"🔗 {invite.invite_link}\n\n"
                    f"Делитесь этой ссылкой, и каждый раз, когда кто-то "
                    f"заходит в канал по вашей ссылке, вы получите уведомление!"
                ),
                reply_markup=get_back_to_menu_keyboard(),
            )

            logger.info(
                f"Создана реферальная ссылка для пользователя {callback.from_user.id}"
            )

        except Exception as e:
            logger.error(f"Ошибка создания ссылки: {e}")
            await callback.message.answer(
                text=(
                    "❌ <b>Произошла ошибка при создании ссылки.</b>\n\n"
                    "Пожалуйста, попробуйте позже или свяжитесь с администрацией."
                ),
                reply_markup=get_back_to_menu_keyboard(),
            )

    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot) -> None:
    """
    Отслеживание участников канала.
    
    Срабатывает когда кто-то вступает или выходит из канала.
    """
    # Проверяем, что это наш канал
    if event.chat.id != settings.channel_id:
        return

    # Получаем статусы
    old_status = event.old_chat_member.status if event.old_chat_member else "left"
    new_status = event.new_chat_member.status if event.new_chat_member else "left"
    user_id = event.new_chat_member.user.id if event.new_chat_member else None

    # === ВСТУПЛЕНИЕ В КАНАЛ ===
    if old_status in ("left", "kicked") and new_status in ("member", "administrator"):
        # Новый участник! Проверяем, есть ли invite_link
        if event.invite_link and event.invite_link.invite_link:
            invite_link = event.invite_link.invite_link
            if user_id:
                owner_telegram_id, counted, referral_link_id = await handle_referral_join(
                    invite_link=invite_link,
                    telegram_id=user_id,
                )

                if owner_telegram_id and counted:
                    await notify_user_new_referral(bot, owner_telegram_id)
                if referral_link_id:
                    await inspect_join_event(
                        bot=bot,
                        telegram_id=user_id,
                        referral_link_id=referral_link_id,
                        owner_telegram_id=owner_telegram_id,
                        counted=counted,
                    )

                logger.info(
                    f"Реферал {user_id} по ссылке {invite_link}. "
                    f"owner={owner_telegram_id or 'unknown'} counted={counted}"
                )
    # === ВЫХОД ИЗ КАНАЛА ===
    elif old_status in ("member", "administrator") and new_status in ("left", "kicked"):
        if user_id:
            referral_link_id, decremented = await handle_referral_leave(user_id)
            if referral_link_id:
                await inspect_leave_event(
                    bot=bot,
                    telegram_id=user_id,
                    referral_link_id=referral_link_id,
                )

            if referral_link_id and decremented:
                logger.info(
                    f"Реферал {user_id} вышел из канала, счётчик умеьшен"
                )


@router.callback_query(lambda c: c.data == "claim_referral_gift")
async def claim_referral_gift(callback: types.CallbackQuery, bot: Bot) -> None:
    """Запрос на выдачу подарка за рефералов."""
    user = await UserRepository.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return
    
    # Получаем реферальную ссылку
    referral = await ReferralRepository.get_by_user_id(user.id)
    
    if not referral:
        await callback.answer("❌ Реферальная ссылка не найдена", show_alert=True)
        return
    
    # Используем сервис для расчёта статистики
    stats = calculate_gift_stats(
        referral_count=referral.referral_count,
        gifts_claimed=referral.gifts_claimed,
    )
    
    if not stats.can_claim:
        await callback.answer("❌ Нет доступных подарков", show_alert=True)
        return
    
    # Отмечаем все доступные подарки как запрошенные
    claimed = await ReferralRepository.claim_available_gifts(
        referral_id=referral.id,
        referrals_per_gift=REFERRALS_PER_GIFT,
    )
    if claimed <= 0:
        await callback.answer("❌ Нет доступных подарков", show_alert=True)
        return
    
    # Уведомляем админа о запросе
    user_mention = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {callback.from_user.id}"
    
    admin_text = (
        f"🎁 <b>Запрос на выдачу подарков!</b>\n\n"
        f"👤 Пользователь: {user_mention}\n"
        f"📊 Всего переходов: <b>{referral.referral_count}</b>\n"
        f"🧸 Подарков к выдаче: <b>{claimed}</b>\n"
        f"📦 Всего получено: <b>{stats.already_claimed + claimed}</b>\n\n"
        f"Свяжитесь с пользователем для выдачи подарка."
    )
    
    try:
        # Отправляем всем админам
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_text)
            except Exception as e:
                logger.warning(f"Не удалось отправить админу {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {e}")
        await callback.answer("❌ Ошибка отправки запроса", show_alert=True)
        return
    
    # Отвечаем пользователю
    gift_word = get_gift_word(claimed)
    
    try:
        await callback.message.edit_text(
            text=(
                f"✅ <b>Запрос на выдачу подарка отправлен!</b>\n\n"
                f"🧸 Вы запросили: <b>{gift_word}</b>\n\n"
                f"Администратор свяжется с вами в ближайшее время для выдачи.\n\n"
                f"Спасибо за участие в реферальной программе!"
            ),
            reply_markup=get_back_to_menu_keyboard(),
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text=(
                f"✅ <b>Запрос на выдачу подарка отправлен!</b>\n\n"
                f"🧸 Вы запросили: <b>{gift_word}</b>\n\n"
                f"Администратор свяжется с вами в ближайшее время для выдачи.\n\n"
                f"Спасибо за участие в реферальной программе!"
            ),
            reply_markup=get_back_to_menu_keyboard(),
        )
    
    try:
        await callback.answer("Запрос отправлен! 🎁")
    except TelegramBadRequest:
        pass
    
    logger.info(
        f"Пользователь {callback.from_user.id} запросил {claimed} подарков "
        f"({referral.referral_count} переходов)"
    )
