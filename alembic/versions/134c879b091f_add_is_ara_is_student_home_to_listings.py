"""add is_ara, is_student_home to listings

Revision ID: 134c879b091f
Revises: b8d2638a5151
Create Date: 2026-04-24 23:50:19.232973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '134c879b091f'
down_revision: Union[str, Sequence[str], None] = 'b8d2638a5151'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listings', sa.Column('is_ara', sa.Boolean(), nullable=True))
    op.add_column('listings', sa.Column('is_student_home', sa.Boolean(), nullable=True))
    op.add_column('user_filters', sa.Column('is_ara', sa.Boolean(), nullable=True))
    op.add_column('user_filters', sa.Column('is_student_home', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_filters', 'is_student_home')
    op.drop_column('user_filters', 'is_ara')
    op.drop_column('listings', 'is_student_home')
    op.drop_column('listings', 'is_ara')
