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

# Антиабьюз (Реалистичные пороги для живого канала)
JOIN_SPIKE_WINDOW_MIN = 5
JOIN_SPIKE_THRESHOLD = 30  # Было 8, стало 30
LEAVE_SPIKE_WINDOW_MIN = 5
LEAVE_SPIKE_THRESHOLD = 20  # Было 5, стало 20
REJOIN_WINDOW_MIN = 60
REJOIN_THRESHOLD = 5  # Было 3, стало 5
FLAG_COOLDOWN_MIN = 60
