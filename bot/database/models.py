from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bot.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей."""

    pass


class User(Base):
    """Пользователь бота."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Связи
    referral_links: Mapped[list["ReferralLink"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ad_requests: Mapped[list["AdvertisingRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ReferralLink(Base):
    """Реферальная ссылка пользователя."""

    __tablename__ = "referral_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    invite_link: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    referral_count: Mapped[int] = mapped_column(default=0)
    gifts_claimed: Mapped[int] = mapped_column(default=0)  # Сколько подарков уже получено
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Связи
    user: Mapped["User"] = relationship(back_populates="referral_links")
    referrals: Mapped[list["Referral"]] = relationship(
        back_populates="referral_link", cascade="all, delete-orphan"
    )


class Referral(Base):
    """Запись о реферале — кто зашёл по чьей ссылке."""

    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    referral_link_id: Mapped[int] = mapped_column(
        ForeignKey("referral_links.id", ondelete="CASCADE")
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)  # Кто зашёл
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Связи
    referral_link: Mapped["ReferralLink"] = relationship(back_populates="referrals")


class ReferralEvent(Base):
    """РЎРѕР±С‹С‚РёСЏ СЂРµС„РµСЂР°Р»Р°: РїРµСЂРІС‹Р№ РІС…РѕРґ, РїРѕРІС‚РѕСЂРЅС‹Р№ РІС…РѕРґ, РІС‹С…РѕРґ."""

    __tablename__ = "referral_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    referral_link_id: Mapped[int] = mapped_column(
        ForeignKey("referral_links.id", ondelete="CASCADE")
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_join_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_join_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    left_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="joined")  # joined/left
    is_counted: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferralActivityLog(Base):
    """Сырой журнал join/leave событий для антиабьюз-аналитики."""

    __tablename__ = "referral_activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referral_link_id: Mapped[int] = mapped_column(
        ForeignKey("referral_links.id", ondelete="CASCADE"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(20), index=True)  # join/leave
    is_rejoin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)


class ReferralAbuseFlag(Base):
    """Флаги подозрительной активности в реферальной системе."""

    __tablename__ = "referral_abuse_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    flag_type: Mapped[str] = mapped_column(String(50), index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    referral_link_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("referral_links.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)


class ReferralDailyStat(Base):
    """Дневная предагрегация активных рефералов по владельцу."""

    __tablename__ = "referral_daily_stats"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "stat_date", name="uq_referral_daily_stats_owner_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    active_referrals: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class AdvertisingRequest(Base):
    """Заявка на рекламу в канале пользователя."""

    __tablename__ = "advertising_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel_link: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Связи
    user: Mapped["User"] = relationship(back_populates="ad_requests")


class AdminActionLog(Base):
    """Минимальный журнал действий админов."""

    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action_type: Mapped[str] = mapped_column(String(50))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column()
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# Создание движка и сессии
class BroadcastJob(Base):
    """Background broadcast job with persisted progress."""

    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    source_chat_id: Mapped[int] = mapped_column(BigInteger)
    source_message_id: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    total_users: Mapped[int] = mapped_column(default=0)
    processed_users: Mapped[int] = mapped_column(default=0)
    sent_count: Mapped[int] = mapped_column(default=0)
    blocked_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    throttle_seconds: Mapped[float] = mapped_column(default=0.05)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Инициализация базы данных (создание таблиц)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
