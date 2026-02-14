"""Add broadcast jobs table

Revision ID: 006_broadcast_jobs
Revises: 005_blocked_abuse
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "006_broadcast_jobs"
down_revision: Union[str, None] = "005_blocked_abuse"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcast_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_admin_id", sa.BigInteger(), nullable=False),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("total_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("throttle_seconds", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broadcast_jobs_created_by_admin_id",
        "broadcast_jobs",
        ["created_by_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_jobs_status",
        "broadcast_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_jobs_status", table_name="broadcast_jobs")
    op.drop_index("ix_broadcast_jobs_created_by_admin_id", table_name="broadcast_jobs")
    op.drop_table("broadcast_jobs")
