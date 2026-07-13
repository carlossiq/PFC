"""replace status with completed on research session

Revision ID: 8f12d6737e91
Revises: a3f9c2d1e8b4
Create Date: 2026-07-13 14:16:18.267498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f12d6737e91'
down_revision: Union[str, Sequence[str], None] = 'a3f9c2d1e8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("research_session", "status")
    op.add_column(
        "research_session",
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("research_session", "completed")
    op.add_column(
        "research_session",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="input"),
    )
