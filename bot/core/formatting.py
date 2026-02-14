from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bot.database.models import User


def format_user_short(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str] = None,
) -> str:
    """
    Форматирование имени пользователя для отображения.
    
    Приоритет:
    1. @username
    2. First Name (ID:123)
    3. ID:123
    """
    if username:
        return f"@{username}"
    if first_name:
        return f"{first_name} (ID:{user_id})"
    return f"ID:{user_id}"


def format_user_model(user: "User") -> str:
    """Форматирование пользователя из модели БД."""
    return format_user_short(
        user_id=user.telegram_id,  # Используем telegram_id, а не внутренний PK
        username=user.username,
        first_name=user.first_name,
    )
