"""add water price, lessor info

Revision ID: 7f9332f97ad9
Revises: 6eacbb3574cf
Create Date: 2026-04-03 23:38:38.045548

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "7f9332f97ad9"
down_revision: Union[str, Sequence[str], None] = "6eacbb3574cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("listings", sa.Column("water_price", sa.Float(), nullable=True))
    op.add_column("listings", sa.Column("lessor_name", sa.String(), nullable=True))
    op.add_column(
        "listings", sa.Column("is_private_lessor", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("listings", "is_private_lessor")
    op.drop_column("listings", "lessor_name")
    op.drop_column("listings", "water_price")
