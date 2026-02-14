"""Константы бизнес-логики бота."""

# Реферальная программа
REFERRALS_PER_GIFT = 5  # Сколько рефералов нужно для 1 подарка

# Статусы заявок на рекламу
class AdRequestStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Обратная совместимость с тестами/старым кодом:
# ранее класс мог называться RequestStatus.
class RequestStatus(AdRequestStatus):
    """Алиас для AdRequestStatus для совместимости."""

# Rate limiting
MAX_AD_REQUESTS_PER_HOUR = 3
MAX_MESSAGES_PER_MINUTE = 30
