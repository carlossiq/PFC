"""create probe_query_term table

Revision ID: 3e22832c4057
Revises: b1c4f0a9d2e7
Create Date: 2026-07-17 23:43:27.746016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e22832c4057'
down_revision: Union[str, Sequence[str], None] = 'b1c4f0a9d2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "probe_query_term",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("probe_query_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_probe_query_term_probe_query_id",
        "probe_query_term",
        "session_probe_query",
        ["probe_query_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_probe_query_term_probe_query_id", "probe_query_term", ["probe_query_id"])
    op.create_unique_constraint(
        "uq_probe_query_term_probe_query_id_term",
        "probe_query_term",
        ["probe_query_id", "term"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_probe_query_term_probe_query_id_term", "probe_query_term", type_="unique")
    op.drop_index("ix_probe_query_term_probe_query_id", table_name="probe_query_term")
    op.drop_constraint("fk_probe_query_term_probe_query_id", "probe_query_term", type_="foreignkey")
    op.drop_table("probe_query_term")
