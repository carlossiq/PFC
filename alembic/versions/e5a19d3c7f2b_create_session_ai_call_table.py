"""create session_ai_call table

Revision ID: e5a19d3c7f2b
Revises: c7e1a2f4b6d9
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a19d3c7f2b'
down_revision: Union[str, Sequence[str], None] = 'c7e1a2f4b6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_ai_call",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_session_ai_call_session_id",
        "session_ai_call",
        "research_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_session_ai_call_session_id", "session_ai_call", ["session_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_session_ai_call_session_id", table_name="session_ai_call")
    op.drop_constraint("fk_session_ai_call_session_id", "session_ai_call", type_="foreignkey")
    op.drop_table("session_ai_call")
