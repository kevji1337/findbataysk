from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню с основными кнопками."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="🎁 Подарок за реф программу",
                callback_data="referral_program",
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Реклама в Вашем ТГК",
                callback_data="advertising",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Топ по приглашениям",
                callback_data="leaderboard",
            )
        ],
        [
            InlineKeyboardButton(
                text="📞 Связь с администрацией",
                callback_data="admin_contact",
            )
        ],
    ]

    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📣 Админ-рассылка",
                    callback_data="admin_broadcast",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_referral_keyboard(can_claim: bool) -> InlineKeyboardMarkup:
    """Клавиатура для реферальной программы."""
    buttons = []

    if can_claim:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🎁 Запрос на выдачу подарка",
                    callback_data="claim_referral_gift",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 В главное меню",
                callback_data="back_to_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ad_criteria_keyboard() -> InlineKeyboardMarkup:
    """Кнопка подтверждения соответствия критериям."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Мой ТГК подходит",
                    callback_data="ad_criteria_confirmed",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


def get_ad_review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Кнопки для админа: принять/отклонить заявку."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"ad_approve:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"ad_reject:{request_id}",
                ),
            ]
        ]
    )


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 В главное меню",
                    callback_data="back_to_menu",
                )
            ]
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены текущего действия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_action",
                )
            ]
        ]
    )


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Топ рефереров",
                    callback_data="admin_top_referrers",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все заявки",
                    callback_data="admin_requests:all",
                ),
                InlineKeyboardButton(
                    text="⏳ Ожидающие",
                    callback_data="admin_requests:pending",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Одобренные",
                    callback_data="admin_requests:approved",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонённые",
                    callback_data="admin_requests:rejected",
                ),
            ],
        ]
    )


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 В админ-панель",
                    callback_data="admin_panel",
                )
            ]
        ]
    )


def get_requests_filter_keyboard(current_filter: str) -> InlineKeyboardMarkup:
    """Кнопки фильтрации заявок с подсветкой текущего фильтра."""
    filters = [
        ("all", "📋 Все"),
        ("pending", "⏳ Ожидающие"),
        ("approved", "✅ Одобренные"),
        ("rejected", "❌ Отклонённые"),
    ]

    buttons = []
    for filter_id, label in filters:
        text = f"• {label} •" if filter_id == current_filter else label
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"admin_requests:{filter_id}",
            )
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[:2],
            buttons[2:],
            [
                InlineKeyboardButton(
                    text="🔙 В админ-панель",
                    callback_data="admin_panel",
                )
            ],
        ]
    )


def get_leaderboard_keyboard(current_period: str) -> InlineKeyboardMarkup:
    """
    Кнопки выбора периода для публичного лидерборда.

    current_period: one of "week", "month", "all"
    """
    periods = [
        ("week", "📅 Неделя"),
        ("month", "🗓 Месяц"),
        ("all", "∞ Всё время"),
    ]

    buttons: list[InlineKeyboardButton] = []
    for period_id, label in periods:
        text = f"• {label} •" if period_id == current_period else label
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"lb:{period_id}",
            )
        )

    rows = [
        buttons[:2],
        buttons[2:],
        [
            InlineKeyboardButton(
                text="🔙 В главное меню",
                callback_data="back_to_menu",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


