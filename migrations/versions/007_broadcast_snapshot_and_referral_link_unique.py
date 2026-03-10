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


def _deduplicate_referral_links() -> None:
    """Слить дубли referral_links.user_id перед созданием unique constraint."""
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE tmp_referral_link_merge AS
            WITH ranked AS (
                SELECT
                    id,
                    user_id,
                    FIRST_VALUE(id) OVER (
                        PARTITION BY user_id
                        ORDER BY referral_count DESC, gifts_claimed DESC, created_at DESC NULLS LAST, id DESC
                    ) AS canonical_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id
                        ORDER BY referral_count DESC, gifts_claimed DESC, created_at DESC NULLS LAST, id DESC
                    ) AS rn
                FROM referral_links
            )
            SELECT
                id AS duplicate_id,
                user_id,
                canonical_id
            FROM ranked
            WHERE rn > 1
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE tmp_referral_link_aggregate AS
            SELECT
                rl.user_id,
                m.canonical_id,
                COALESCE(SUM(rl.referral_count), 0) AS total_referral_count,
                COALESCE(SUM(rl.gifts_claimed), 0) AS total_gifts_claimed
            FROM referral_links rl
            JOIN (
                SELECT DISTINCT user_id, canonical_id
                FROM tmp_referral_link_merge
            ) m ON m.user_id = rl.user_id
            GROUP BY rl.user_id, m.canonical_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE tmp_referral_event_conflicts AS
            SELECT
                m.canonical_id,
                source.telegram_id,
                MIN(source.first_join_at) AS min_first_join_at,
                MAX(source.last_join_at) AS max_last_join_at,
                MAX(source.left_at) AS max_left_at,
                BOOL_OR(source.is_counted) AS any_is_counted,
                BOOL_OR(source.status <> 'left') AS has_active_source
            FROM referral_events source
            JOIN tmp_referral_link_merge m
                ON m.duplicate_id = source.referral_link_id
            JOIN referral_events target
                ON target.referral_link_id = m.canonical_id
               AND target.telegram_id = source.telegram_id
            GROUP BY m.canonical_id, source.telegram_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referral_events AS target
            SET
                first_join_at = LEAST(target.first_join_at, conflict.min_first_join_at),
                last_join_at = CASE
                    WHEN target.last_join_at IS NULL THEN conflict.max_last_join_at
                    WHEN conflict.max_last_join_at IS NULL THEN target.last_join_at
                    ELSE GREATEST(target.last_join_at, conflict.max_last_join_at)
                END,
                left_at = CASE
                    WHEN target.left_at IS NULL THEN conflict.max_left_at
                    WHEN conflict.max_left_at IS NULL THEN target.left_at
                    ELSE GREATEST(target.left_at, conflict.max_left_at)
                END,
                status = CASE
                    WHEN target.status <> 'left' OR conflict.has_active_source THEN 'joined'
                    ELSE 'left'
                END,
                is_counted = target.is_counted OR conflict.any_is_counted
            FROM tmp_referral_event_conflicts conflict
            WHERE target.referral_link_id = conflict.canonical_id
              AND target.telegram_id = conflict.telegram_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM referral_events source
            USING tmp_referral_link_merge m, referral_events target
            WHERE source.referral_link_id = m.duplicate_id
              AND target.referral_link_id = m.canonical_id
              AND target.telegram_id = source.telegram_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referral_events e
            SET referral_link_id = m.canonical_id
            FROM tmp_referral_link_merge m
            WHERE e.referral_link_id = m.duplicate_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referrals r
            SET referral_link_id = m.canonical_id
            FROM tmp_referral_link_merge m
            WHERE r.referral_link_id = m.duplicate_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM referrals older
            USING referrals newer
            WHERE older.telegram_id = newer.telegram_id
              AND older.id < newer.id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referral_activity_logs log
            SET referral_link_id = m.canonical_id
            FROM tmp_referral_link_merge m
            WHERE log.referral_link_id = m.duplicate_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referral_abuse_flags flag
            SET referral_link_id = m.canonical_id
            FROM tmp_referral_link_merge m
            WHERE flag.referral_link_id = m.duplicate_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE referral_links canonical
            SET
                gifts_claimed = aggregate.total_gifts_claimed,
                referral_count = GREATEST(
                    aggregate.total_referral_count,
                    COALESCE(events.active_referrals, 0)
                )
            FROM tmp_referral_link_aggregate aggregate
            LEFT JOIN (
                SELECT
                    referral_link_id,
                    COUNT(*) FILTER (WHERE is_counted IS TRUE) AS active_referrals
                FROM referral_events
                GROUP BY referral_link_id
            ) events ON events.referral_link_id = aggregate.canonical_id
            WHERE canonical.id = aggregate.canonical_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM referral_links rl
            USING tmp_referral_link_merge m
            WHERE rl.id = m.duplicate_id
            """
        )
    )


def upgrade() -> None:
    op.add_column(
        "broadcast_jobs",
        sa.Column("recipient_ids_json", sa.Text(), nullable=True),
    )
    _deduplicate_referral_links()
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
