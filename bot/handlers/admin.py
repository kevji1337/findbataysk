"""Админ-панель: статистика, история заявок и рассылка."""

from datetime import UTC, datetime, timedelta

from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.config import settings
from bot.core.formatting import format_user_model
from bot.database.repository import (
    AdminActionLogRepository,
    AdvertisingRepository,
    BroadcastJobRepository,
    ReferralStatsRepository,
    UserRepository,
)
from bot.keyboards.inline import (
    get_admin_panel_keyboard,
    get_back_to_admin_keyboard,
    get_broadcast_confirm_keyboard,
    get_cancel_keyboard,
    get_requests_filter_keyboard,
)
from bot.states.admin_broadcast import AdminBroadcastStates

router = Router(name="admin")

# Все хендлеры этого роутера доступны только админам.
router.message.filter(lambda msg: settings.is_admin(msg.from_user.id))
router.callback_query.filter(lambda cb: settings.is_admin(cb.from_user.id))


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_private_chat(chat: types.Chat | None) -> bool:
    return getattr(chat, "type", None) == "private"


def _is_draft_expired(created_at_raw: str | None) -> bool:
    if not created_at_raw:
        return True

    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError:
        return True

    ttl = max(1, int(settings.broadcast_draft_ttl_seconds))
    return _utcnow() - created_at > timedelta(seconds=ttl)


def _get_admin_panel_text(stats: dict, pending_count: int) -> str:
    """Сформировать текст админ-панели."""
    return (
        "🔐 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['users_count']}</b>\n"
        f"🔗 Реферальных ссылок: <b>{stats['links_count']}</b>\n"
        f"➡️ Всего переходов: <b>{stats['total_referrals']}</b>\n\n"
        f"📋 Заявок на рекламу ожидает: <b>{pending_count}</b>"
    )


@router.message(Command("admin"))
async def admin_panel(message: types.Message) -> None:
    """Показать админ-панель."""
    stats = await ReferralStatsRepository.get_total_stats()
    pending_count = await AdvertisingRepository.get_pending_count()
    text = _get_admin_panel_text(stats, pending_count)
    await message.answer(text, reply_markup=get_admin_panel_keyboard())


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel_callback(callback: types.CallbackQuery) -> None:
    """Показать админ-панель (callback)."""
    stats = await ReferralStatsRepository.get_total_stats()
    pending_count = await AdvertisingRepository.get_pending_count()
    text = _get_admin_panel_text(stats, pending_count)

    try:
        await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard())
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_top_referrers")
async def show_top_referrers(callback: types.CallbackQuery) -> None:
    """Показать топ рефереров."""
    top_referrers = await ReferralStatsRepository.get_top_referrers(limit=10)

    if not top_referrers:
        text = "📊 <b>Топ рефереров</b>\n\n🤷 Пока нет данных"
    else:
        lines = ["📊 <b>Топ рефереров</b>\n"]
        for i, (user, count) in enumerate(top_referrers, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            lines.append(f"{medal} {format_user_model(user)} — <b>{count}</b> чел.")
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_requests:"))
async def show_requests_history(callback: types.CallbackQuery) -> None:
    """Показать историю заявок на рекламу."""
    _, filter_type = callback.data.split(":")
    status_filter = None if filter_type == "all" else filter_type

    requests = await AdvertisingRepository.get_all_requests(
        limit=15,
        status_filter=status_filter,
    )

    if not requests:
        text = f"📋 <b>История заявок</b> ({filter_type})\n\n🤷 Заявок нет"
    else:
        lines = [f"📋 <b>История заявок</b> ({filter_type})\n"]
        for req, user in requests:
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
            }.get(req.status, "❓")

            lines.append(
                f"{status_emoji} {format_user_model(user)}\n"
                f"   📎 {req.channel_link}\n"
                f"   📅 {req.created_at.strftime('%d.%m %H:%M')}"
            )
        text = "\n\n".join(lines)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_requests_filter_keyboard(filter_type),
            disable_web_page_preview=True,
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Запуск админ-рассылки из главного меню."""
    if not _is_private_chat(callback.message.chat if callback.message else None):
        await state.clear()
        await callback.answer("Откройте бота в личных сообщениях", show_alert=True)
        return

    await state.set_state(AdminBroadcastStates.waiting_message)
    await state.update_data(broadcast_started_at=_utcnow().isoformat())

    text = (
        "📣 <b>Рассылка пользователям</b>\n\n"
        "Отправьте одно сообщение (текст/фото/видео), затем отдельно подтвердите запуск рассылки."
    )
    try:
        await callback.message.edit_text(text=text, reply_markup=get_cancel_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(text=text, reply_markup=get_cancel_keyboard())

    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def admin_broadcast_send(message: types.Message, state: FSMContext, bot: Bot) -> None:
    """Принять сообщение для рассылки и запросить подтверждение."""
    del bot

    if not settings.is_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён.")
        return

    if not _is_private_chat(message.chat):
        await state.clear()
        await message.answer("Рассылку можно запускать только из личного чата с ботом.")
        return

    state_data = await state.get_data()
    if _is_draft_expired(state_data.get("broadcast_started_at")):
        await state.clear()
        await message.answer(
            "Черновик рассылки истёк. Откройте раздел рассылки заново."
        )
        return

    await state.update_data(
        broadcast_source_chat_id=message.chat.id,
        broadcast_source_message_id=message.message_id,
        broadcast_started_at=_utcnow().isoformat(),
    )
    await state.set_state(AdminBroadcastStates.waiting_confirmation)

    await message.answer(
        "Сообщение сохранено. Подтвердите запуск рассылки ниже.",
        reply_markup=get_broadcast_confirm_keyboard(),
    )
    logger.info("broadcast_draft_saved admin={}", message.from_user.id)


@router.callback_query(
    AdminBroadcastStates.waiting_confirmation,
    lambda c: c.data == "admin_broadcast_confirm",
)
async def admin_broadcast_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Поставить подтверждённую рассылку в очередь."""
    state_data = await state.get_data()
    if _is_draft_expired(state_data.get("broadcast_started_at")):
        await state.clear()
        await callback.answer("Черновик истёк. Создайте рассылку заново.", show_alert=True)
        return

    source_chat_id = state_data.get("broadcast_source_chat_id")
    source_message_id = state_data.get("broadcast_source_message_id")
    if not source_chat_id or not source_message_id:
        await state.clear()
        await callback.answer("Черновик не найден. Создайте рассылку заново.", show_alert=True)
        return

    user_ids = await UserRepository.get_broadcast_telegram_ids()
    if not user_ids:
        await state.clear()
        await callback.message.answer("Нет пользователей для рассылки.")
        await callback.answer()
        return

    job = await BroadcastJobRepository.create(
        admin_telegram_id=callback.from_user.id,
        source_chat_id=int(source_chat_id),
        source_message_id=int(source_message_id),
        total_users=len(user_ids),
        recipient_ids=user_ids,
        throttle_seconds=settings.broadcast_throttle_seconds,
        max_retries=settings.broadcast_max_retries,
    )

    await AdminActionLogRepository.create(
        admin_telegram_id=callback.from_user.id,
        action_type="broadcast_queued",
        target_type="broadcast_job",
        target_id=job.id,
        details=f"total_users={len(user_ids)}",
    )

    await state.clear()

    text = (
        "📬 <b>Рассылка поставлена в очередь</b>\n\n"
        f"Job ID: <b>{job.id}</b>\n"
        f"Пользователей к обработке: <b>{len(user_ids)}</b>\n\n"
        "Отдельное сообщение придет после завершения."
    )
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

    await callback.answer("Рассылка запущена")
    logger.info(
        "broadcast_queued admin={} job_id={} total={}",
        callback.from_user.id,
        job.id,
        len(user_ids),
    )
