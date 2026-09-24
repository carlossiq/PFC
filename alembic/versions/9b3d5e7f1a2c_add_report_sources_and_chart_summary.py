"""add session_report_section.sources and session_chart.summary

Revision ID: 9b3d5e7f1a2c
Revises: 7c4e2a91f6b8
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b3d5e7f1a2c'
down_revision: Union[str, Sequence[str], None] = '7c4e2a91f6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("session_report_section", sa.Column("sources", sa.JSON(), nullable=True))
    op.add_column("session_chart", sa.Column("summary", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("session_chart", "summary")
    op.drop_column("session_report_section", "sources")
