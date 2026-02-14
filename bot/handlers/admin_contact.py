from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import settings


router = Router(name="admin_contact")


@router.callback_query(lambda c: c.data == "admin_contact")
async def admin_contact(callback: types.CallbackQuery) -> None:
    """Показать контактную информацию администрации."""
    # Формируем ссылку на ЛС админа
    admin_link = f"tg://user?id={settings.admin_id}"
    
    # Клавиатура с кнопкой-ссылкой на админа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ Написать администратору",
                    url=admin_link,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 В главное меню",
                    callback_data="back_to_menu",
                )
            ],
        ]
    )
    
    # Удаляем предыдущее сообщение (может быть фото)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    
    await callback.message.answer(
        text=(
            "📞 <b>Связь с администрацией</b>\n\n"
            "Нажмите кнопку ниже, чтобы написать администратору.\n\n"
            "Мы ответим вам в ближайшее время!"
        ),
        reply_markup=keyboard,
    )
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


