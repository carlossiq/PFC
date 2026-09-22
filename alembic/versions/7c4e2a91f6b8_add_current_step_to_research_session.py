"""add current_step/current_substep to research_session

Revision ID: 7c4e2a91f6b8
Revises: 3f1c8b7a9d2e
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c4e2a91f6b8'
down_revision: Union[str, Sequence[str], None] = '3f1c8b7a9d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "research_session",
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("research_session", sa.Column("current_substep", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("research_session", "current_substep")
    op.drop_column("research_session", "current_step")
