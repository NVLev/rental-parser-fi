"""fix_column_lengths

Revision ID: 7f55986adf8f
Revises: d373e8745d31
Create Date: 2026-04-17 22:40:38.750883

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f55986adf8f"
down_revision: Union[str, Sequence[str], None] = "d373e8745d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
