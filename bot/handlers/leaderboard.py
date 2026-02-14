from time import perf_counter
from typing import Literal

from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.database.repository import ReferralStatsRepository
from bot.keyboards.inline import get_leaderboard_keyboard
from bot.services.leaderboard_cache import (
    get_cached_leaderboard_text,
    set_cached_leaderboard_text,
)


router = Router(name="leaderboard")

LeaderboardPeriod = Literal["week", "month", "all"]


PERIOD_TITLES: dict[str, str] = {
    "week": "за неделю",
    "month": "за месяц",
    "all": "за всё время",
}

PERIOD_LIMITS: dict[str, int] = {
    "week": 3,
    "month": 3,
    "all": 10,
}


def _is_message_not_modified_error(exc: TelegramBadRequest) -> bool:
    text = str(exc).lower()
    return "message is not modified" in text


def _format_user_display(user: "object") -> str:
    """
    Сформировать отображаемое имя пользователя для лидерборда.

    Приоритет:
    - username
    - first_name
    - telegram_id
    """
    username = getattr(user, "username", None)
    first_name = getattr(user, "first_name", None)
    telegram_id = getattr(user, "telegram_id", None)

    if username:
        return f"@{username}"
    if first_name:
        return f"{first_name} (ID:{telegram_id})"
    return f"ID:{telegram_id}"


async def _render_leaderboard(
    callback: types.CallbackQuery,
    period: LeaderboardPeriod,
) -> None:
    """Общий рендер лидерборда для различных периодов."""
    request_started = perf_counter()

    callback_ack_started = perf_counter()
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass
    callback_ack_ms = (perf_counter() - callback_ack_started) * 1000

    cache_lookup_started = perf_counter()
    cached_text = get_cached_leaderboard_text(period)
    cache_lookup_ms = (perf_counter() - cache_lookup_started) * 1000

    if cached_text is not None:
        keyboard = get_leaderboard_keyboard(current_period=period)
        delivery_started = perf_counter()
        try:
            await callback.message.edit_text(text=cached_text, reply_markup=keyboard)
        except TelegramBadRequest as exc:
            if not _is_message_not_modified_error(exc):
                await callback.message.answer(text=cached_text, reply_markup=keyboard)

        delivery_ms = (perf_counter() - delivery_started) * 1000
        total_ms = (perf_counter() - request_started) * 1000
        logger.info(
            "leaderboard_timing period={} cache_hit={} rows={} total_ms={:.2f} "
            "callback_ack_ms={:.2f} cache_lookup_ms={:.2f} db_query_ms={:.2f} "
            "render_ms={:.2f} delivery_ms={:.2f}",
            period,
            True,
            0,
            total_ms,
            callback_ack_ms,
            cache_lookup_ms,
            0.0,
            0.0,
            delivery_ms,
        )
        return

    db_started = perf_counter()
    limit = PERIOD_LIMITS.get(period, 3)
    rows = await ReferralStatsRepository.get_top_referrers_by_period(
        period=period,
        limit=limit,
    )
    db_query_ms = (perf_counter() - db_started) * 1000

    render_started = perf_counter()
    title_suffix = PERIOD_TITLES.get(period, PERIOD_TITLES["all"])
    header = f"🏆 <b>Топ приглашений {title_suffix}</b>\n"

    if not rows:
        text = header + "\nПока нет данных для отображения."
    else:
        lines: list[str] = [header, ""]
        for index, (user, total) in enumerate(rows, start=1):
            medal = (
                "🥇"
                if index == 1
                else "🥈"
                if index == 2
                else "🥉"
                if index == 3
                else f"{index}."
            )
            display = _format_user_display(user)
            lines.append(f"{medal} {display} — <b>{total}</b> приглашений")

        lines.append(
            "\nℹ️ В зачёт идут только актуальные рефералы, "
            "которые не отписались от канала."
        )

        text = "\n".join(lines)

    render_ms = (perf_counter() - render_started) * 1000

    set_cached_leaderboard_text(period, text)

    keyboard = get_leaderboard_keyboard(current_period=period)
    delivery_started = perf_counter()
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if not _is_message_not_modified_error(exc):
            await callback.message.answer(text=text, reply_markup=keyboard)

    delivery_ms = (perf_counter() - delivery_started) * 1000
    total_ms = (perf_counter() - request_started) * 1000
    logger.info(
        "leaderboard_timing period={} cache_hit={} rows={} total_ms={:.2f} "
        "callback_ack_ms={:.2f} cache_lookup_ms={:.2f} db_query_ms={:.2f} "
        "render_ms={:.2f} delivery_ms={:.2f}",
        period,
        False,
        len(rows),
        total_ms,
        callback_ack_ms,
        cache_lookup_ms,
        db_query_ms,
        render_ms,
        delivery_ms,
    )


@router.callback_query(lambda c: c.data == "leaderboard")
async def show_leaderboard_default(callback: types.CallbackQuery) -> None:
    """Открыть лидерборд (по умолчанию — за всё время)."""
    await _render_leaderboard(callback, period="all")


@router.callback_query(lambda c: c.data.startswith("lb:"))
async def change_leaderboard_period(callback: types.CallbackQuery) -> None:
    """Переключение периода лидерборда."""
    try:
        _, period = callback.data.split(":", 1)
    except (ValueError, AttributeError):
        period = "all"

    if period == "day":
        period = "week"

    if period not in ("week", "month", "all"):
        period = "all"

    await _render_leaderboard(callback, period=period)
