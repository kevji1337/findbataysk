from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext

from bot.handlers.start import cmd_start


@pytest.mark.asyncio
async def test_cmd_start_new_user():
    """Проверка обработчика /start для нового пользователя."""
    # 1. Подготовка моков (Mock Objects)
    
    # Мок сообщения от пользователя
    message = AsyncMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 12345
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.answer_photo = AsyncMock() # Заглушка для отправки фото
    message.answer = AsyncMock()       # Заглушка для отправки текста

    # Мок состояния (FSM)
    state = AsyncMock(spec=FSMContext)

    # 2. Патчинг (подмена) зависимостей внутри функции
    # Мы подменяем реальные классы/функции на заглушки, чтобы не лезть в БД/диск.
    with patch("bot.handlers.start.UserRepository") as MockUserRepo, \
         patch("bot.handlers.start.settings") as MockSettings, \
         patch("bot.handlers.start.FSInputFile") as MockFSInputFile, \
         patch("bot.handlers.start.WELCOME_PHOTO") as MockPhotoPath, \
         patch("bot.handlers.start.get_main_menu_keyboard") as MockKeyboard:

        # Настраиваем поведение моков
        MockSettings.is_admin.return_value = False  # Юзер не админ
        MockPhotoPath.exists.return_value = True    # Файл фото якобы существует

        # 3. Вызов тестируемой функции
        await cmd_start(message, state)

        # 4. Проверки (Assertions)
        
        # Проверяем, что состояние было очищено
        state.clear.assert_awaited_once()

        # Проверяем, что пользователь был создан в БД (или получен)
        MockUserRepo.get_or_create.assert_awaited_once_with(
            telegram_id=12345,
            username="test_user",
            first_name="Test",
        )

        # Проверяем, что было отправлено фото (так как WELCOME_PHOTO.exists() == True)
        message.answer_photo.assert_awaited_once()
        
        # Получаем аргументы вызова отправки фото
        args, kwargs = message.answer_photo.call_args
        assert kwargs["caption"] is not None # Убеждаемся, что есть текст
        assert kwargs["reply_markup"] is not None # Убеждаемся, что есть клавиатура

@pytest.mark.asyncio
async def test_cmd_start_no_photo():
    """Проверка /start, если фото приветствия отсутствует."""
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 12345
    message.answer_photo = AsyncMock()
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)

    with patch("bot.handlers.start.UserRepository") as MockUserRepo, \
         patch("bot.handlers.start.settings"), \
         patch("bot.handlers.start.WELCOME_PHOTO") as MockPhotoPath, \
         patch("bot.handlers.start.get_main_menu_keyboard"):

        # Симулируем отсутствие файла
        MockPhotoPath.exists.return_value = False

        await cmd_start(message, state)

        # Должен вызвать answer (текст), а не answer_photo
        message.answer.assert_awaited_once()
        message.answer_photo.assert_not_called()
