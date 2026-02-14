"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])

    # Referral links table
    op.create_table(
        'referral_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('invite_link', sa.String(255), nullable=False),
        sa.Column('referral_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('gifts_claimed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_link'),
    )
    op.create_index('ix_referral_links_invite_link', 'referral_links', ['invite_link'])

    # Referrals table (who joined via whose link)
    op.create_table(
        'referrals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_link_id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['referral_link_id'], ['referral_links.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_referrals_telegram_id', 'referrals', ['telegram_id'])

    # Referral events table (first join / rejoin / leave)
    op.create_table(
        'referral_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_link_id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('first_join_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_join_at', sa.DateTime(), nullable=True),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='joined'),
        sa.Column('is_counted', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['referral_link_id'], ['referral_links.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
    )
    op.create_index('ix_referral_events_telegram_id', 'referral_events', ['telegram_id'])

    # Advertising requests table
    op.create_table(
        'advertising_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel_link', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('advertising_requests')
    op.drop_table('referral_events')
    op.drop_table('referrals')
    op.drop_table('referral_links')
    op.drop_table('users')
