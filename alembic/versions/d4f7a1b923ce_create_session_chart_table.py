"""create session_chart table

Revision ID: d4f7a1b923ce
Revises: a1c4f9b2d7e3
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f7a1b923ce'
down_revision: Union[str, Sequence[str], None] = 'a1c4f9b2d7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_chart",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("probe_query_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("chart_type", sa.String(length=50), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False, server_default="image/png"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_session_chart_probe_query_id",
        "session_chart",
        "session_probe_query",
        ["probe_query_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_session_chart_probe_query_id", "session_chart", ["probe_query_id"])
    op.create_unique_constraint(
        "uq_session_chart_probe_query_id_chart_type", "session_chart", ["probe_query_id", "chart_type"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_session_chart_probe_query_id_chart_type", "session_chart", type_="unique")
    op.drop_index("ix_session_chart_probe_query_id", table_name="session_chart")
    op.drop_constraint("fk_session_chart_probe_query_id", "session_chart", type_="foreignkey")
    op.drop_table("session_chart")
