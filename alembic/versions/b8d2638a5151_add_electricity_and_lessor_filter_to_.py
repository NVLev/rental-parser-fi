"""add electricity and lessor filter to user_filters

Revision ID: b8d2638a5151
Revises: 7f55986adf8f
Create Date: 2026-04-19 17:37:13.964361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d2638a5151'
down_revision: Union[str, Sequence[str], None] = '7f55986adf8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_filters', sa.Column('electricity_included_only', sa.Boolean(), nullable=False))
    op.add_column('user_filters', sa.Column('is_private_lessor', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_filters', 'is_private_lessor')
    op.drop_column('user_filters', 'electricity_included_only')
