"""add fit_quality to session_chart

Revision ID: 3f1c8b7a9d2e
Revises: 9a2c4e6f1b3d
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f1c8b7a9d2e'
down_revision: Union[str, Sequence[str], None] = '9a2c4e6f1b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("session_chart", sa.Column("fit_quality", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("session_chart", "fit_quality")
