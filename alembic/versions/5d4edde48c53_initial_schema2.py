"""Initial schema2

Revision ID: 5d4edde48c53
Revises: 937abd5477dd
Create Date: 2026-04-01 22:46:57.200898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d4edde48c53'
down_revision: Union[str, Sequence[str], None] = '937abd5477dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('listings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.String(length=50), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('area', sa.Float(), nullable=True),
    sa.Column('district', sa.String(length=100), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('room_count', sa.String(length=30), nullable=True),
    sa.Column('room_structure', sa.String(length=100), nullable=True),
    sa.Column('water_included', sa.Boolean(), nullable=True),
    sa.Column('electricity_included', sa.Boolean(), nullable=True),
    sa.Column('floor_plan_url', sa.String(length=500), nullable=True),
    sa.Column('available_from', sa.String(length=50), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('scraped_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listings_external_id'), 'listings', ['external_id'], unique=True)
    op.create_table('user_filters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('price_min', sa.Float(), nullable=True),
    sa.Column('price_max', sa.Float(), nullable=True),
    sa.Column('area_min', sa.Float(), nullable=True),
    sa.Column('area_max', sa.Float(), nullable=True),
    sa.Column('districts', sa.String(length=500), nullable=True),
    sa.Column('room_counts', sa.String(length=200), nullable=True),
    sa.Column('water_included_only', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_filters_user_id'), 'user_filters', ['user_id'], unique=False)
    op.create_table('seen_listings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('listing_id', sa.Integer(), nullable=False),
    sa.Column('notified_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'listing_id', name='uq_user_listing')
    )
    op.create_index(op.f('ix_seen_listings_user_id'), 'seen_listings', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_seen_listings_user_id'), table_name='seen_listings')
    op.drop_table('seen_listings')
    op.drop_index(op.f('ix_user_filters_user_id'), table_name='user_filters')
    op.drop_table('user_filters')
    op.drop_index(op.f('ix_listings_external_id'), table_name='listings')
    op.drop_table('listings')
