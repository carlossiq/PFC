"""create session_probe_query table

Revision ID: a3f9c2d1e8b4
Revises: bd51ccb747ab
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f9c2d1e8b4'
down_revision: Union[str, Sequence[str], None] = 'bd51ccb747ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_probe_query",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("fonte", sa.String(length=20), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=True),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("complexity_score", sa.Float(), nullable=True),
        sa.Column("complexity_level", sa.String(length=50), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_session_probe_query_session_id",
        "session_probe_query",
        "research_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_session_probe_query_session_id", "session_probe_query", ["session_id"])
    op.create_unique_constraint(
        "uq_session_probe_query_session_fonte", "session_probe_query", ["session_id", "fonte"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_session_probe_query_session_fonte", "session_probe_query", type_="unique")
    op.drop_index("ix_session_probe_query_session_id", table_name="session_probe_query")
    op.drop_constraint("fk_session_probe_query_session_id", "session_probe_query", type_="foreignkey")
    op.drop_table("session_probe_query")
