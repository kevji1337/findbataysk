"""Add broadcast recipients snapshot and unique referral link per user

Revision ID: 007_broadcast_snapshot
Revises: 006_broadcast_jobs
Create Date: 2026-03-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "007_broadcast_snapshot"
down_revision: Union[str, None] = "006_broadcast_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "broadcast_jobs",
        sa.Column("recipient_ids_json", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_referral_links_user_id",
        "referral_links",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_referral_links_user_id",
        "referral_links",
        type_="unique",
    )
    op.drop_column("broadcast_jobs", "recipient_ids_json")
