"""Константы бизнес-логики бота."""

# Реферальная программа
REFERRALS_PER_GIFT = 5  # Сколько рефералов нужно для 1 подарка

# Статусы заявок на рекламу
class AdRequestStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Rate limiting
MAX_AD_REQUESTS_PER_HOUR = 3
MAX_MESSAGES_PER_MINUTE = 30

# Антиабьюз
JOIN_SPIKE_WINDOW_MIN = 5
JOIN_SPIKE_THRESHOLD = 8
LEAVE_SPIKE_WINDOW_MIN = 5
LEAVE_SPIKE_THRESHOLD = 5
REJOIN_WINDOW_MIN = 60
REJOIN_THRESHOLD = 3
FLAG_COOLDOWN_MIN = 30
