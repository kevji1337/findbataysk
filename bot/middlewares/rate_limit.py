"""Rate limiting middleware для защиты от спама."""

from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from bot.core.constants import MAX_AD_REQUESTS_PER_HOUR, MAX_MESSAGES_PER_MINUTE


class LRUDict(OrderedDict):
    """OrderedDict с ограничением максимального размера (LRU-кэш)."""
    
    def __init__(self, max_size: int = 10000, *args, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)
    
    def __setitem__(self, key, value):
        # Если ключ уже есть, перемещаем в конец
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        # Удаляем старые записи если превышен лимит
        while len(self) > self.max_size:
            self.popitem(last=False)
    
    def get_or_create(self, key, default_factory=list):
        """Получить значение или создать новое."""
        if key not in self:
            self[key] = default_factory()
        else:
            # Перемещаем в конец при доступе (LRU)
            self.move_to_end(key)
        return self[key]


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов.
    
    Настройки по умолчанию (из constants.py):
    - Максимум 3 заявки на рекламу в час
    - Максимум 30 сообщений в минуту
    
    Защита от утечки памяти:
    - Максимум 10000 пользователей в кэше
    - LRU-eviction для старых записей
    """
    
    MAX_USERS = 10000  # Максимум пользователей в кэше
    
    def __init__(
        self,
        max_ad_requests_per_hour: int = MAX_AD_REQUESTS_PER_HOUR,
        max_messages_per_minute: int = MAX_MESSAGES_PER_MINUTE,
    ):
        self.max_ad_requests = max_ad_requests_per_hour
        self.max_messages = max_messages_per_minute
        
        # LRU-словари для защиты от memory leak
        self.ad_requests: LRUDict = LRUDict(max_size=self.MAX_USERS)
        self.messages: LRUDict = LRUDict(max_size=self.MAX_USERS)
    
    def _cleanup_old_entries(
        self, 
        entries: list[datetime], 
        window: timedelta
    ) -> list[datetime]:
        """Удалить старые записи за пределами окна."""
        now = datetime.now()
        return [ts for ts in entries if now - ts < window]
    
    def check_rate_limit(
        self,
        user_id: int,
        action_type: str = "message"
    ) -> tuple[bool, int]:
        """
        Проверить rate limit для пользователя.
        
        Returns:
            (allowed: bool, seconds_until_reset: int)
        """
        now = datetime.now()
        
        if action_type == "ad_request":
            # Очистка старых записей (окно 1 час)
            window = timedelta(hours=1)
            entries = self.ad_requests.get_or_create(user_id, list)
            entries = self._cleanup_old_entries(entries, window)
            self.ad_requests[user_id] = entries
            
            if len(entries) >= self.max_ad_requests:
                oldest = min(entries)
                reset_time = oldest + window
                seconds_left = int((reset_time - now).total_seconds())
                return False, max(0, seconds_left)
            
            return True, 0
        
        else:  # message
            # Очистка старых записей (окно 1 минута)
            window = timedelta(minutes=1)
            entries = self.messages.get_or_create(user_id, list)
            entries = self._cleanup_old_entries(entries, window)
            self.messages[user_id] = entries
            
            if len(entries) >= self.max_messages:
                oldest = min(entries)
                reset_time = oldest + window
                seconds_left = int((reset_time - now).total_seconds())
                return False, max(0, seconds_left)
            
            return True, 0
    
    def record_action(self, user_id: int, action_type: str = "message") -> None:
        """Записать действие пользователя."""
        now = datetime.now()
        if action_type == "ad_request":
            entries = self.ad_requests.get_or_create(user_id, list)
            entries.append(now)
        else:
            entries = self.messages.get_or_create(user_id, list)
            entries.append(now)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Обработка события с проверкой rate limit."""
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if user_id:
            allowed, seconds_left = self.check_rate_limit(user_id, "message")
            
            if not allowed:
                if isinstance(event, Message):
                    await event.answer(
                        f"⏳ Слишком много запросов. Подожди {seconds_left} сек."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⏳ Подожди {seconds_left} сек.",
                        show_alert=True
                    )
                return None
            
            self.record_action(user_id, "message")
        
        # Передаём middleware в data для использования в handlers
        data["rate_limiter"] = self
        
        return await handler(event, data)


# Глобальный экземпляр rate limiter
rate_limiter = RateLimitMiddleware()
