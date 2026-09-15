"""create session_report_section and session_report tables

Revision ID: f2b7c4a91d6e
Revises: 567d7fd94fe3
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b7c4a91d6e'
down_revision: Union[str, Sequence[str], None] = '567d7fd94fe3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_report_section",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("section_key", sa.String(length=50), nullable=False),
        sa.Column("rag_context", sa.Text(), nullable=True),
        sa.Column("generated_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="rag_done"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_session_report_section_session_id",
        "session_report_section",
        "research_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_session_report_section_session_id", "session_report_section", ["session_id"])
    op.create_unique_constraint(
        "uq_session_report_section_session_id_section_key",
        "session_report_section",
        ["session_id", "section_key"],
    )

    op.create_table(
        "session_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("tex_object_key", sa.String(length=500), nullable=False),
        sa.Column("pdf_object_key", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="tex_ready"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_session_report_session_id",
        "session_report",
        "research_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_session_report_session_id", "session_report", ["session_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_session_report_session_id", "session_report", type_="unique")
    op.drop_constraint("fk_session_report_session_id", "session_report", type_="foreignkey")
    op.drop_table("session_report")

    op.drop_constraint(
        "uq_session_report_section_session_id_section_key", "session_report_section", type_="unique"
    )
    op.drop_index("ix_session_report_section_session_id", table_name="session_report_section")
    op.drop_constraint("fk_session_report_section_session_id", "session_report_section", type_="foreignkey")
    op.drop_table("session_report_section")
