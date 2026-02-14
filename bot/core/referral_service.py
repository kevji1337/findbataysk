"""Сервис для работы с реферальной программой."""

from dataclasses import dataclass

from bot.core.constants import REFERRALS_PER_GIFT


@dataclass
class GiftStats:
    """Статистика подарков пользователя."""
    
    total_earned: int  # Всего заработано подарков
    already_claimed: int  # Уже получено
    available: int  # Доступно к получению
    until_next: int  # Сколько рефералов до следующего подарка
    can_claim: bool  # Можно ли запросить подарок


def calculate_gift_stats(referral_count: int, gifts_claimed: int) -> GiftStats:
    """
    Рассчитать статистику подарков для пользователя.
    
    Args:
        referral_count: Количество рефералов
        gifts_claimed: Количество уже полученных подарков
        
    Returns:
        GiftStats с полной статистикой
    """
    total_earned = referral_count // REFERRALS_PER_GIFT
    available = total_earned - gifts_claimed
    next_gift_at = (total_earned + 1) * REFERRALS_PER_GIFT
    until_next = next_gift_at - referral_count
    
    return GiftStats(
        total_earned=total_earned,
        already_claimed=gifts_claimed,
        available=available,
        until_next=until_next,
        can_claim=available > 0,
    )


def get_gift_word(count: int) -> str:
    """
    Получить правильное склонение слова 'мишка' для текста пользователю.

    Функция возвращает только слово (без числа), чтобы его можно было
    использовать как в тестах, так и в человекочитаемых фразах.
    """
    n = abs(count) % 100
    n1 = n % 10

    # Исключения 11–14
    if 11 <= n <= 14:
        return "мишек"

    if n1 == 1:
        return "мишку"
    if 2 <= n1 <= 4:
        return "мишки"
    return "мишек"
