"""Add leaderboard performance indexes

Revision ID: 004_leaderboard_perf_indexes
Revises: 003_referral_daily_stats
Create Date: 2026-02-12
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "004_leaderboard_perf_indexes"
down_revision: Union[str, None] = "003_referral_daily_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_referral_daily_stats_stat_date_owner_user_id",
        "referral_daily_stats",
        ["stat_date", "owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_referral_links_user_id_referral_count",
        "referral_links",
        ["user_id", "referral_count"],
        unique=False,
    )
    op.create_index(
        "ix_referral_events_first_join_at_is_counted_referral_link_id",
        "referral_events",
        ["first_join_at", "is_counted", "referral_link_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_referral_events_first_join_at_is_counted_referral_link_id",
        table_name="referral_events",
    )
    op.drop_index(
        "ix_referral_links_user_id_referral_count",
        table_name="referral_links",
    )
    op.drop_index(
        "ix_referral_daily_stats_stat_date_owner_user_id",
        table_name="referral_daily_stats",
    )
