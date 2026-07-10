"""add name column to research_session

Revision ID: bd51ccb747ab
Revises: 24476815f379
Create Date: 2026-07-10 19:08:56.476144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd51ccb747ab'
down_revision: Union[str, Sequence[str], None] = '24476815f379'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("research_session", sa.Column("name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("research_session", "name")
