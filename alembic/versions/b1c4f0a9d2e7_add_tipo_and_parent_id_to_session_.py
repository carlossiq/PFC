"""add tipo and parent_id to session_probe_query (self-relationship)

Revision ID: b1c4f0a9d2e7
Revises: 7cff2afc0f3c
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c4f0a9d2e7'
down_revision: Union[str, Sequence[str], None] = '7cff2afc0f3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("session_probe_query", sa.Column("tipo", sa.String(length=20), nullable=True))
    op.add_column("session_probe_query", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_session_probe_query_parent_id",
        "session_probe_query",
        "session_probe_query",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_session_probe_query_session_fonte", "session_probe_query", type_="unique")
    op.create_unique_constraint(
        "uq_session_probe_query_session_fonte_tipo",
        "session_probe_query",
        ["session_id", "fonte", "tipo"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_session_probe_query_session_fonte_tipo", "session_probe_query", type_="unique")
    op.create_unique_constraint(
        "uq_session_probe_query_session_fonte", "session_probe_query", ["session_id", "fonte"]
    )
    op.drop_constraint("fk_session_probe_query_parent_id", "session_probe_query", type_="foreignkey")
    op.drop_column("session_probe_query", "parent_id")
    op.drop_column("session_probe_query", "tipo")
