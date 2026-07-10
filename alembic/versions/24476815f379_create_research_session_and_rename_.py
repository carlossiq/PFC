"""create research_session and rename param_init to session_input

Revision ID: 24476815f379
Revises:
Create Date: 2026-07-10 18:06:55.981578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core.config import settings


# revision identifiers, used by Alembic.
revision: str = '24476815f379'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "research_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="input"),
        sa.Column("patent_source", sa.String(length=50), nullable=True),
        sa.Column("scholarly_source", sa.String(length=50), nullable=True),
        sa.Column(
            "relevance_threshold",
            sa.Float(),
            nullable=False,
            server_default=str(settings.relevance_threshold),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_research_session_public_id", "research_session", ["public_id"], unique=True)

    # param_init existia apenas como rascunho efêmero de wizard (descartado ao
    # cancelar/fechar aba) - linhas remanescentes não têm session_id (conceito
    # não existia) e não representam sessões reais, por isso são descartadas
    # antes da coluna se tornar not null.
    op.execute("DELETE FROM param_init")

    op.rename_table("param_init", "session_input")
    op.alter_column("session_input", "tema", new_column_name="theme")
    op.alter_column("session_input", "descricao", new_column_name="description")
    op.alter_column("session_input", "area_estudo", new_column_name="area_of_study")

    op.add_column("session_input", sa.Column("session_id", sa.Integer(), nullable=False))
    op.add_column("session_input", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column("session_input", sa.Column("year_from", sa.Integer(), nullable=True))
    op.add_column("session_input", sa.Column("year_to", sa.Integer(), nullable=True))
    op.add_column(
        "session_input",
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_foreign_key(
        "fk_session_input_session_id", "session_input", "research_session", ["session_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_session_input_parent_id", "session_input", "session_input", ["parent_id"], ["id"]
    )
    op.create_index("ix_session_input_session_id", "session_input", ["session_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_session_input_session_id", table_name="session_input")
    op.drop_constraint("fk_session_input_parent_id", "session_input", type_="foreignkey")
    op.drop_constraint("fk_session_input_session_id", "session_input", type_="foreignkey")

    op.drop_column("session_input", "iterations")
    op.drop_column("session_input", "year_to")
    op.drop_column("session_input", "year_from")
    op.drop_column("session_input", "parent_id")
    op.drop_column("session_input", "session_id")

    op.alter_column("session_input", "area_of_study", new_column_name="area_estudo")
    op.alter_column("session_input", "description", new_column_name="descricao")
    op.alter_column("session_input", "theme", new_column_name="tema")
    op.rename_table("session_input", "param_init")

    op.drop_index("ix_research_session_public_id", table_name="research_session")
    op.drop_table("research_session")
