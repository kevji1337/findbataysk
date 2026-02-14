"""
Тесты для core модулей.

Запуск: pytest tests/ -v
"""

import pytest

from bot.core.constants import (
    REFERRALS_PER_GIFT,
    RequestStatus,
)
from bot.core.referral_service import (
    GiftStats,
    calculate_gift_stats,
    get_gift_word,
)


class TestConstants:
    """Тесты для констант."""
    
    def test_referrals_per_gift_is_positive(self):
        """REFERRALS_PER_GIFT должен быть положительным."""
        assert REFERRALS_PER_GIFT > 0
    
    def test_request_status_values(self):
        """RequestStatus должен иметь все нужные статусы."""
        assert RequestStatus.PENDING == "pending"
        assert RequestStatus.APPROVED == "approved"
        assert RequestStatus.REJECTED == "rejected"


class TestGiftStats:
    """Тесты для GiftStats dataclass."""
    
    def test_gift_stats_creation(self):
        """Создание GiftStats."""
        stats = GiftStats(
            total_earned=2,
            already_claimed=1,
            available=1,
            until_next=3,
            can_claim=True,
        )
        assert stats.total_earned == 2
        assert stats.available == 1
        assert stats.can_claim is True


class TestCalculateGiftStats:
    """Тесты для calculate_gift_stats."""
    
    def test_no_referrals(self):
        """При 0 переходах нет подарков."""
        stats = calculate_gift_stats(referral_count=0, gifts_claimed=0)
        
        assert stats.total_earned == 0
        assert stats.available == 0
        assert stats.can_claim is False
        assert stats.until_next == 5  # До первого подарка 5 переходов
    
    def test_not_enough_referrals(self):
        """При 3 переходах ещё нет подарка."""
        stats = calculate_gift_stats(referral_count=3, gifts_claimed=0)
        
        assert stats.total_earned == 0
        assert stats.available == 0
        assert stats.can_claim is False
        assert stats.until_next == 2  # До подарка ещё 2 перехода
    
    def test_exactly_five_referrals(self):
        """При 5 переходах — 1 подарок."""
        stats = calculate_gift_stats(referral_count=5, gifts_claimed=0)
        
        assert stats.total_earned == 1
        assert stats.available == 1
        assert stats.can_claim is True
    
    def test_claimed_gift(self):
        """После получения подарка — 0 доступно."""
        stats = calculate_gift_stats(referral_count=5, gifts_claimed=1)
        
        assert stats.total_earned == 1
        assert stats.already_claimed == 1
        assert stats.available == 0
        assert stats.can_claim is False
        assert stats.until_next == 5  # До следующего подарка 5 переходов
    
    def test_multiple_gifts(self):
        """При 12 переходах — 2 подарка."""
        stats = calculate_gift_stats(referral_count=12, gifts_claimed=0)
        
        assert stats.total_earned == 2
        assert stats.available == 2
        assert stats.can_claim is True
        assert stats.until_next == 3  # До третьего подарка 3 перехода
    
    def test_partial_claim(self):
        """Частичное получение подарков."""
        stats = calculate_gift_stats(referral_count=17, gifts_claimed=2)
        
        assert stats.total_earned == 3  # 17 // 5 = 3
        assert stats.already_claimed == 2
        assert stats.available == 1
        assert stats.can_claim is True


class TestGetGiftWord:
    """Тесты для склонения слова 'мишка'."""
    
    def test_one_gift(self):
        """1 мишку."""
        assert get_gift_word(1) == "мишку"
    
    def test_two_gifts(self):
        """2 мишки."""
        assert get_gift_word(2) == "мишки"
    
    def test_three_gifts(self):
        """3 мишки."""
        assert get_gift_word(3) == "мишки"
    
    def test_four_gifts(self):
        """4 мишки."""
        assert get_gift_word(4) == "мишки"
    
    def test_five_gifts(self):
        """5 мишек."""
        assert get_gift_word(5) == "мишек"
    
    def test_eleven_gifts(self):
        """11 мишек (исключение)."""
        assert get_gift_word(11) == "мишек"
    
    def test_twenty_one_gifts(self):
        """21 мишку."""
        assert get_gift_word(21) == "мишку"
    
    def test_twenty_two_gifts(self):
        """22 мишки."""
        assert get_gift_word(22) == "мишки"
    
    def test_twenty_five_gifts(self):
        """25 мишек."""
        assert get_gift_word(25) == "мишек"
