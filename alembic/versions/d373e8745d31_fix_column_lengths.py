"""fix_column_lengths

Revision ID: d373e8745d31
Revises: bad95c50f714
Create Date: 2026-04-17 22:37:26.081350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd373e8745d31'
down_revision: Union[str, Sequence[str], None] = 'bad95c50f714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('listings', 'lessor_name',
        existing_type=sa.TEXT(),
        type_=sa.String(250),
        existing_nullable=True)
    op.alter_column('listings', 'district',
        existing_type=sa.String(150),
        type_=sa.String(200),
        existing_nullable=True)
    op.alter_column('listings', 'room_structure',
        existing_type=sa.String(100),
        type_=sa.String(150),
        existing_nullable=True)

def downgrade() -> None:
    op.alter_column('listings', 'room_structure',
        existing_type=sa.String(150),
        type_=sa.String(100),
        existing_nullable=True)
    op.alter_column('listings', 'district',
        existing_type=sa.String(200),
        type_=sa.String(150),
        existing_nullable=True)
    op.alter_column('listings', 'lessor_name',
        existing_type=sa.String(250),
        type_=sa.TEXT(),
        existing_nullable=True)
