from pathlib import Path
from typing import Union

from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from bot.config import settings
from bot.database.repository import UserRepository
from bot.keyboards.inline import get_main_menu_keyboard

router = Router(name="start")

WELCOME_PHOTO = Path(__file__).parent.parent / "media" / "welcome.jpg"

WELCOME_MESSAGE = """👋 <b>Привет!</b>

В этом боте тебе будут платить за рекламу нашего ТГК!"""


def _is_message_not_modified_error(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def send_welcome(
    target: Union[types.Message, types.CallbackQuery],
    *,
    as_new_message: bool = False,
) -> None:
    """Отправить/обновить приветственное меню без лишних дубликатов."""
    user_id = target.from_user.id
    keyboard = get_main_menu_keyboard(is_admin=settings.is_admin(user_id))

    if isinstance(target, types.CallbackQuery):
        if not as_new_message:
            # Предпочитаем редактировать текущее сообщение, чтобы не плодить новые меню.
            if WELCOME_PHOTO.exists() and getattr(target.message, "photo", None):
                try:
                    await target.message.edit_caption(
                        caption=WELCOME_MESSAGE,
                        reply_markup=keyboard,
                    )
                    return
                except TelegramBadRequest as e:
                    if _is_message_not_modified_error(e):
                        return
            else:
                try:
                    await target.message.edit_text(
                        text=WELCOME_MESSAGE,
                        reply_markup=keyboard,
                    )
                    return
                except TelegramBadRequest as e:
                    if _is_message_not_modified_error(e):
                        return

        # Fallback: отправляем новое меню только если редактирование невозможно.
        if WELCOME_PHOTO.exists():
            await target.message.answer_photo(
                photo=FSInputFile(WELCOME_PHOTO),
                caption=WELCOME_MESSAGE,
                reply_markup=keyboard,
            )
        else:
            await target.message.answer(
                text=WELCOME_MESSAGE,
                reply_markup=keyboard,
            )
        return

    # /start
    if WELCOME_PHOTO.exists():
        await target.answer_photo(
            photo=FSInputFile(WELCOME_PHOTO),
            caption=WELCOME_MESSAGE,
            reply_markup=keyboard,
        )
    else:
        await target.answer(
            text=WELCOME_MESSAGE,
            reply_markup=keyboard,
        )


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Обработчик команды /start."""
    await state.clear()

    await UserRepository.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    await send_welcome(message)


@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Вернуться в главное меню."""
    await state.clear()
    await send_welcome(callback)

    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


@router.callback_query(lambda c: c.data == "cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Отменить текущее действие."""
    await state.clear()
    await send_welcome(callback)

    try:
        await callback.answer("Действие отменено")
    except TelegramBadRequest:
        pass
