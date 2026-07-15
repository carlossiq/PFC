"""add country to patent and affiliation_countries to article

Revision ID: 7cff2afc0f3c
Revises: e5a19d3c7f2b
Create Date: 2026-07-15 11:21:19.761830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cff2afc0f3c'
down_revision: Union[str, Sequence[str], None] = 'e5a19d3c7f2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("patent", sa.Column("country", sa.String(length=10), nullable=True))
    op.add_column("article", sa.Column("affiliation_countries", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("article", "affiliation_countries")
    op.drop_column("patent", "country")
