from types import SimpleNamespace

import pytest

from bot.core.formatting import format_user_model, format_user_short


def test_format_user_short_username():
    """Форматирование с юзернеймом."""
    assert format_user_short(123, "alice", "Alice") == "@alice"


def test_format_user_short_firstname():
    """Форматирование без юзернейма, но с именем."""
    assert format_user_short(123, None, "Bob") == "Bob (ID:123)"
    assert format_user_short(123, "", "Bob") == "Bob (ID:123)"


def test_format_user_short_id_only():
    """Форматирование только по ID."""
    assert format_user_short(123, None, None) == "ID:123"
    assert format_user_short(123, "", "") == "ID:123"


def test_format_user_model():
    """Тест форматирования из модели (mock)."""
    # Эмулируем модель User через SimpleNamespace
    u1 = SimpleNamespace(telegram_id=111, username="test_user", first_name="Test")
    assert format_user_model(u1) == "@test_user"

    u2 = SimpleNamespace(telegram_id=222, username=None, first_name="John")
    assert format_user_model(u2) == "John (ID:222)"

    u3 = SimpleNamespace(telegram_id=333, username=None, first_name=None)
    assert format_user_model(u3) == "ID:333"
