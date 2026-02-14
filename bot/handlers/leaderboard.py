from typing import Literal

from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.core.formatting import format_user_model
from bot.database.repository import ReferralStatsRepository
from bot.keyboards.inline import get_leaderboard_keyboard


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
    return "message is not modified" in str(exc).lower()




async def _render_leaderboard(
    callback: types.CallbackQuery,
    period: LeaderboardPeriod,
) -> None:
    """Рендер лидерборда для выбранного периода."""
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

    limit = PERIOD_LIMITS.get(period, 3)
    rows = await ReferralStatsRepository.get_top_referrers_by_period(
        period=period,
        limit=limit,
    )

    title_suffix = PERIOD_TITLES.get(period, PERIOD_TITLES["all"])
    header = f"🏆 <b>Топ приглашений {title_suffix}</b>\n"

    if not rows:
        text = header + "\nПока нет данных для отображения."
    else:
        lines: list[str] = [header, ""]
        for index, (user, total) in enumerate(rows, start=1):
            medal = (
                "🥇" if index == 1
                else "🥈" if index == 2
                else "🥉" if index == 3
                else f"{index}."
            )
            display = format_user_model(user)
            lines.append(f"{medal} {display} — <b>{total}</b> приглашений")

        lines.append(
            "\nℹ️ В зачёт идут только актуальные рефералы, "
            "которые не отписались от канала."
        )
        text = "\n".join(lines)

    keyboard = get_leaderboard_keyboard(current_period=period)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if not _is_message_not_modified_error(exc):
            await callback.message.answer(text=text, reply_markup=keyboard)


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
