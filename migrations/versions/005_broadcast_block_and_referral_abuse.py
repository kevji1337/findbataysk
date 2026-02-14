"""Add broadcast blocked users and referral anti-abuse tables

Revision ID: 005_blocked_abuse
Revises: 004_leaderboard_perf_indexes
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "005_blocked_abuse"
down_revision: Union[str, None] = "004_leaderboard_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("bot_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_bot_blocked", "users", ["bot_blocked"], unique=False)

    op.create_table(
        "referral_activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("referral_link_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("is_rejoin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_activity_logs_telegram_id", "referral_activity_logs", ["telegram_id"], unique=False)
    op.create_index("ix_referral_activity_logs_referral_link_id", "referral_activity_logs", ["referral_link_id"], unique=False)
    op.create_index("ix_referral_activity_logs_action", "referral_activity_logs", ["action"], unique=False)
    op.create_index("ix_referral_activity_logs_created_at", "referral_activity_logs", ["created_at"], unique=False)

    op.create_table(
        "referral_abuse_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flag_type", sa.String(length=50), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("referral_link_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_abuse_flags_flag_type", "referral_abuse_flags", ["flag_type"], unique=False)
    op.create_index("ix_referral_abuse_flags_telegram_id", "referral_abuse_flags", ["telegram_id"], unique=False)
    op.create_index("ix_referral_abuse_flags_referral_link_id", "referral_abuse_flags", ["referral_link_id"], unique=False)
    op.create_index("ix_referral_abuse_flags_created_at", "referral_abuse_flags", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_referral_abuse_flags_created_at", table_name="referral_abuse_flags")
    op.drop_index("ix_referral_abuse_flags_referral_link_id", table_name="referral_abuse_flags")
    op.drop_index("ix_referral_abuse_flags_telegram_id", table_name="referral_abuse_flags")
    op.drop_index("ix_referral_abuse_flags_flag_type", table_name="referral_abuse_flags")
    op.drop_table("referral_abuse_flags")

    op.drop_index("ix_referral_activity_logs_created_at", table_name="referral_activity_logs")
    op.drop_index("ix_referral_activity_logs_action", table_name="referral_activity_logs")
    op.drop_index("ix_referral_activity_logs_referral_link_id", table_name="referral_activity_logs")
    op.drop_index("ix_referral_activity_logs_telegram_id", table_name="referral_activity_logs")
    op.drop_table("referral_activity_logs")

    op.drop_index("ix_users_bot_blocked", table_name="users")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "bot_blocked")
