"""Add referral daily stats table

Revision ID: 003_referral_daily_stats
Revises: 002_admin_action_logs
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "003_referral_daily_stats"
down_revision: Union[str, None] = "002_admin_action_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_daily_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("active_referrals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "stat_date", name="uq_referral_daily_stats_owner_date"),
    )
    op.create_index(
        "ix_referral_daily_stats_owner_user_id",
        "referral_daily_stats",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_referral_daily_stats_stat_date",
        "referral_daily_stats",
        ["stat_date"],
    )

    # Backfill текущих активных рефералов для периодических лидербордов.
    op.execute(
        sa.text(
            """
            INSERT INTO referral_daily_stats (owner_user_id, stat_date, active_referrals)
            SELECT
                rl.user_id AS owner_user_id,
                DATE(re.first_join_at) AS stat_date,
                COUNT(*) AS active_referrals
            FROM referral_events re
            JOIN referral_links rl ON rl.id = re.referral_link_id
            WHERE re.is_counted = TRUE
            GROUP BY rl.user_id, DATE(re.first_join_at)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_referral_daily_stats_stat_date", table_name="referral_daily_stats")
    op.drop_index("ix_referral_daily_stats_owner_user_id", table_name="referral_daily_stats")
    op.drop_table("referral_daily_stats")
