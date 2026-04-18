"""Initial schema

Revision ID: 937abd5477dd
Revises:
Create Date: 2026-03-30 23:52:21.823302

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "937abd5477dd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
