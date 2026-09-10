"""add projection_years to session_chart

Revision ID: 567d7fd94fe3
Revises: d4f7a1b923ce
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '567d7fd94fe3'
down_revision: Union[str, Sequence[str], None] = 'd4f7a1b923ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("session_chart", sa.Column("projection_years", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("session_chart", "projection_years")
