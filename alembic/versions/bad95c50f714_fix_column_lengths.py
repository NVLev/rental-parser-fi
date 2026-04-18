"""fix column lengths

Revision ID: bad95c50f714
Revises: 9a7d5aac733d
Create Date: 2026-04-17 11:14:58.542634

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "bad95c50f714"
down_revision: Union[str, Sequence[str], None] = "9a7d5aac733d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "listings",
        "district",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=150),
        existing_nullable=True,
    )
    op.alter_column(
        "listings",
        "address",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.String(length=300),
        existing_nullable=True,
    )
    op.alter_column(
        "listings",
        "floor_plan_url",
        existing_type=sa.VARCHAR(length=500),
        type_=sa.String(length=1000),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "listings",
        "floor_plan_url",
        existing_type=sa.String(length=1000),
        type_=sa.VARCHAR(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "listings",
        "address",
        existing_type=sa.String(length=300),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "listings",
        "district",
        existing_type=sa.String(length=150),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )
