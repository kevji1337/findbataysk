"""Репозитории базы данных — разбиты по доменам."""

from bot.database.repositories.user_repo import UserRepository
from bot.database.repositories.referral_repo import ReferralRepository
from bot.database.repositories.advertising_repo import AdvertisingRepository
from bot.database.repositories.referral_stats_repo import ReferralStatsRepository
from bot.database.repositories.referral_abuse_repo import ReferralAbuseRepository
from bot.database.repositories.admin_log_repo import AdminActionLogRepository
from bot.database.repositories.broadcast_repo import BroadcastJobRepository

__all__ = [
    "UserRepository",
    "ReferralRepository",
    "AdvertisingRepository",
    "ReferralStatsRepository",
    "ReferralAbuseRepository",
    "AdminActionLogRepository",
    "BroadcastJobRepository",
]
