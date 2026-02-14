"""Админ-панель: статистика, история заявок и рассылка."""

from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.config import settings
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
    get_cancel_keyboard,
    get_requests_filter_keyboard,
)
from bot.states.admin_broadcast import AdminBroadcastStates

router = Router(name="admin")

# ── Фильтр: ВСЕ хендлеры этого роутера доступны только админам ──
router.message.filter(lambda msg: settings.is_admin(msg.from_user.id))
router.callback_query.filter(lambda cb: settings.is_admin(cb.from_user.id))


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


from bot.core.formatting import format_user_model

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
    await state.set_state(AdminBroadcastStates.waiting_message)

    text = (
        "📣 <b>Рассылка пользователям</b>\n\n"
        "Отправьте одно сообщение (текст/фото/видео), и я разошлю его всем пользователям бота."
    )
    try:
        await callback.message.edit_text(text=text, reply_markup=get_cancel_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(text=text, reply_markup=get_cancel_keyboard())

    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def admin_broadcast_send(message: types.Message, state: FSMContext, bot: Bot) -> None:
    """Поставить сообщение в очередь фоновой рассылки."""
    user_ids = await UserRepository.get_broadcast_telegram_ids()
    if not user_ids:
        await state.clear()
        await message.answer("Нет пользователей для рассылки.")
        return

    job = await BroadcastJobRepository.create(
        admin_telegram_id=message.from_user.id,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        total_users=len(user_ids),
        throttle_seconds=settings.broadcast_throttle_seconds,
        max_retries=settings.broadcast_max_retries,
    )

    await AdminActionLogRepository.create(
        admin_telegram_id=message.from_user.id,
        action_type="broadcast_queued",
        target_type="broadcast_job",
        target_id=job.id,
        details=f"total_users={len(user_ids)}",
    )

    await message.answer(
        (
            "📬 <b>Рассылка поставлена в очередь</b>\n\n"
            f"Job ID: <b>{job.id}</b>\n"
            f"Пользователей к обработке: <b>{len(user_ids)}</b>\n\n"
            "Отдельное сообщение придет после завершения."
        )
    )
    await state.clear()

    logger.info(
        "broadcast_queued admin={} job_id={} total={}",
        message.from_user.id,
        job.id,
        len(user_ids),
    )
