"""add assemble_payload to session_report

Revision ID: 9a2c4e6f1b3d
Revises: f2b7c4a91d6e
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a2c4e6f1b3d'
down_revision: Union[str, Sequence[str], None] = 'f2b7c4a91d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("session_report", sa.Column("assemble_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("session_report", "assemble_payload")
