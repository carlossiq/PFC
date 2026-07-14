"""create patent, article and probe_query association tables

Revision ID: c7e1a2f4b6d9
Revises: 8f12d6737e91
Create Date: 2026-07-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e1a2f4b6d9'
down_revision: Union[str, Sequence[str], None] = '8f12d6737e91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "patent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedup_key", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("publication_number", sa.String(length=100), nullable=True),
        sa.Column("application_number", sa.String(length=100), nullable=True),
        sa.Column("family_id", sa.String(length=100), nullable=True),
        sa.Column("applicants", sa.JSON(), nullable=True),
        sa.Column("inventors", sa.JSON(), nullable=True),
        sa.Column("ipc_codes", sa.JSON(), nullable=True),
        sa.Column("cpc_codes", sa.JSON(), nullable=True),
        sa.Column("filing_date", sa.String(length=10), nullable=True),
        sa.Column("publication_date", sa.String(length=10), nullable=True),
        sa.Column("grant_date", sa.String(length=10), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("legal_status", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patent_dedup_key", "patent", ["dedup_key"], unique=True)

    op.create_table(
        "article",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedup_key", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=True),
        sa.Column("affiliations", sa.JSON(), nullable=True),
        sa.Column("journal_or_source", sa.String(length=500), nullable=True),
        sa.Column("volume", sa.String(length=50), nullable=True),
        sa.Column("issue", sa.String(length=50), nullable=True),
        sa.Column("pages", sa.String(length=50), nullable=True),
        sa.Column("publication_date", sa.String(length=10), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("field_of_study", sa.JSON(), nullable=True),
        sa.Column("citations", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_article_dedup_key", "article", ["dedup_key"], unique=True)

    op.create_table(
        "probe_query_patent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("probe_query_id", sa.Integer(), nullable=False),
        sa.Column("patent_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_probe_query_patent_probe_query_id",
        "probe_query_patent",
        "session_probe_query",
        ["probe_query_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_probe_query_patent_patent_id",
        "probe_query_patent",
        "patent",
        ["patent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_probe_query_patent_probe_query_id", "probe_query_patent", ["probe_query_id"])
    op.create_index("ix_probe_query_patent_patent_id", "probe_query_patent", ["patent_id"])
    op.create_unique_constraint(
        "uq_probe_query_patent_probe_query_id_patent_id",
        "probe_query_patent",
        ["probe_query_id", "patent_id"],
    )

    op.create_table(
        "probe_query_article",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("probe_query_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        "fk_probe_query_article_probe_query_id",
        "probe_query_article",
        "session_probe_query",
        ["probe_query_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_probe_query_article_article_id",
        "probe_query_article",
        "article",
        ["article_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_probe_query_article_probe_query_id", "probe_query_article", ["probe_query_id"])
    op.create_index("ix_probe_query_article_article_id", "probe_query_article", ["article_id"])
    op.create_unique_constraint(
        "uq_probe_query_article_probe_query_id_article_id",
        "probe_query_article",
        ["probe_query_id", "article_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_probe_query_article_probe_query_id_article_id", "probe_query_article", type_="unique")
    op.drop_index("ix_probe_query_article_article_id", table_name="probe_query_article")
    op.drop_index("ix_probe_query_article_probe_query_id", table_name="probe_query_article")
    op.drop_constraint("fk_probe_query_article_article_id", "probe_query_article", type_="foreignkey")
    op.drop_constraint("fk_probe_query_article_probe_query_id", "probe_query_article", type_="foreignkey")
    op.drop_table("probe_query_article")

    op.drop_constraint("uq_probe_query_patent_probe_query_id_patent_id", "probe_query_patent", type_="unique")
    op.drop_index("ix_probe_query_patent_patent_id", table_name="probe_query_patent")
    op.drop_index("ix_probe_query_patent_probe_query_id", table_name="probe_query_patent")
    op.drop_constraint("fk_probe_query_patent_patent_id", "probe_query_patent", type_="foreignkey")
    op.drop_constraint("fk_probe_query_patent_probe_query_id", "probe_query_patent", type_="foreignkey")
    op.drop_table("probe_query_patent")

    op.drop_index("ix_article_dedup_key", table_name="article")
    op.drop_table("article")

    op.drop_index("ix_patent_dedup_key", table_name="patent")
    op.drop_table("patent")
