from typing import List, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация бота из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    channel_id: int
    
    # Сырое значение из окружения, например "111,222,333".
    # Парсим вручную, чтобы не зависеть от JSON-формата.
    admin_ids_env: Optional[str] = Field(
        default=None,
        alias="ADMIN_IDS",
        description="Raw ADMIN_IDS env string, e.g. '111,222,333'",
    )

    # Нормализованный список админов (используется в коде)
    # Алиас задаём так, чтобы окружение его не подхватывало напрямую.
    admin_ids: List[int] = Field(default_factory=list, alias="__ADMIN_IDS_INTERNAL")
    
    # Для обратной совместимости (deprecated)
    admin_id: int = 0
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    leaderboard_cache_ttl_seconds: float = 30.0
    redis_url: str = "redis://localhost:6379/0"
    broadcast_throttle_seconds: float = 0.05
    broadcast_max_retries: int = 3
    broadcast_worker_poll_seconds: float = 1.0

    # Критерии для рекламы (можно переопределить в .env)
    ad_criteria: str = """📋 Минимальные критерии для рекламы в Вашем ТГК:

• Минимум 50 подписчиков
• Аудитория должна быть из Батайска
• Канал не должен нарушать правила Telegram"""

    @field_validator("admin_ids_env", mode="before")
    @classmethod
    def ensure_str(cls, v: Union[str, List[int], int, None]) -> Optional[str]:
        """
        Приводим ADMIN_IDS к строке, чтобы избежать JSON-парсинга
        вида "111,222,333" как complex value.
        """
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, int):
            return str(v)
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return str(v)

    @model_validator(mode="after")
    def build_admin_ids(self) -> "Settings":
        """Собираем финальный список admin_ids из admin_ids_env и admin_id."""
        ids: List[int] = []

        raw = self.admin_ids_env
        if raw:
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    ids.append(int(part))
                except ValueError:
                    # Игнорируем некорректные значения
                    continue

        # Обратная совместимость: legacy ADMIN_ID
        if self.admin_id and self.admin_id not in ids:
            ids.insert(0, self.admin_id)

        self.admin_ids = ids

        # Если список не пуст, первый — главный админ
        if self.admin_ids and not self.admin_id:
            self.admin_id = self.admin_ids[0]

        return self

    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь админом."""
        return user_id in self.admin_ids


settings = Settings()
