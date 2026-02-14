"""
Тесты для конфигурации.
"""

import pytest


class TestSettingsAdminIds:
    """Тесты для парсинга admin_ids."""
    
    def test_single_admin_id_from_admin_id(self, monkeypatch):
        """Один админ через ADMIN_ID."""
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("CHANNEL_ID", "-100123456")
        monkeypatch.setenv("ADMIN_ID", "111222333")
        monkeypatch.delenv("ADMIN_IDS", raising=False)
        
        # Перезагружаем модуль для подхвата новых env
        import importlib
        import bot.config
        importlib.reload(bot.config)
        
        from bot.config import Settings
        settings = Settings(_env_file=None)
        
        assert settings.admin_ids == [111222333]
    
    def test_multiple_admins_from_admin_ids(self, monkeypatch):
        """Несколько админов через ADMIN_IDS."""
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("CHANNEL_ID", "-100123456")
        monkeypatch.setenv("ADMIN_IDS", "111,222,333")
        monkeypatch.delenv("ADMIN_ID", raising=False)
        
        import importlib
        import bot.config
        importlib.reload(bot.config)
        
        from bot.config import Settings
        settings = Settings(_env_file=None)
        
        assert settings.admin_ids == [111, 222, 333]
    
    def test_is_admin_returns_true_for_admin(self, monkeypatch):
        """is_admin возвращает True для админа."""
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("CHANNEL_ID", "-100123456")
        monkeypatch.setenv("ADMIN_IDS", "111,222,333")
        
        import importlib
        import bot.config
        importlib.reload(bot.config)
        
        from bot.config import Settings
        settings = Settings(_env_file=None)
        
        assert settings.is_admin(111) is True
        assert settings.is_admin(222) is True
        assert settings.is_admin(333) is True
    
    def test_is_admin_returns_false_for_non_admin(self, monkeypatch):
        """is_admin возвращает False для не-админа."""
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("CHANNEL_ID", "-100123456")
        monkeypatch.setenv("ADMIN_IDS", "111,222,333")
        
        import importlib
        import bot.config
        importlib.reload(bot.config)
        
        from bot.config import Settings
        settings = Settings(_env_file=None)
        
        assert settings.is_admin(999) is False
        assert settings.is_admin(0) is False
