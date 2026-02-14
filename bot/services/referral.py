import re
from typing import Optional


def validate_channel_link(link: str) -> bool:
    """
    Проверить валидность ссылки на Telegram канал.
    
    Поддерживаемые форматы:
    - https://t.me/channel_name
    - t.me/channel_name
    - @channel_name
    - https://t.me/+invite_code
    - https://t.me/joinchat/invite_code
    """
    patterns = [
        r"^https?://t\.me/[a-zA-Z0-9_]{5,}$",  # Публичный канал
        r"^t\.me/[a-zA-Z0-9_]{5,}$",  # Без https
        r"^@[a-zA-Z0-9_]{5,}$",  # @username
        r"^https?://t\.me/\+[a-zA-Z0-9_-]+$",  # Приватная ссылка с +
        r"^https?://t\.me/joinchat/[a-zA-Z0-9_-]+$",  # Старый формат joinchat
    ]
    
    for pattern in patterns:
        if re.match(pattern, link.strip()):
            return True
    
    return False


def extract_channel_username(link: str) -> Optional[str]:
    """Извлечь username канала из ссылки."""
    link = link.strip()
    
    # @username
    if link.startswith("@"):
        return link[1:]
    
    # https://t.me/channel_name или t.me/channel_name
    match = re.match(r"^(?:https?://)?t\.me/([a-zA-Z0-9_]{5,})$", link)
    if match:
        return match.group(1)
    
    return None
