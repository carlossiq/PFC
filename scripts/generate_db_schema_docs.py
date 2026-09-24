"""
Gera notes/db_schema_atual.{dbml,md,html} a partir dos modelos SQLAlchemy
(fonte da verdade) - sem isso a documentação do schema ficava para trás a
cada migration (session_chart/session_report* nunca chegaram a entrar).

Grupos documentados:
    1. Sessão de prospecção - db/research_session_models.py (Alembic)
    4. Configuração editável - db/config_models.py (create_all + seed)
Os grupos legados (2 e 3) só aparecem nas observações.

Uso:
    python scripts/generate_db_schema_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db.config_models as config_models  # noqa: E402
import db.research_session_models as session_models  # noqa: E402

NOTES_DIR = Path(__file__).resolve().parents[1] / "notes"

# (tabela, coluna) -> nota curta exibida no diagrama.
COLUMN_NOTES: dict[tuple[str, str], str] = {
    ("research_session", "completed_at"): "setado uma vez, quando completed vira true",
    ("research_session", "current_step"): "passo do wizard onde a sessão parou (retomada)",
    ("research_session", "current_substep"): "subpasso do wizard (retomada)",
    ("session_input", "parent_id"): "self - refino do input raiz",
    ("session_probe_query", "fonte"): "ops | scopus",
    ("session_probe_query", "tipo"): "null=probe | specific|balanced|generic",
    ("session_probe_query", "parent_id"): "self - query final refina a query probe",
    ("session_probe_query", "result_count"): "tamanho da amostra baixada",
    ("session_chart", "document_type"): "patent | article",
    ("session_chart", "chart_type"): "s_curve|yearly_volume|top_depositants|top_institutions|top10_heatmap",
    ("session_chart", "object_key"): "PNG no MinIO",
    ("session_chart", "projection_years"): "só s_curve",
    ("session_chart", "fit_quality"): "só s_curve: r_squared/reliable/warning",
    ("session_chart", "summary"): "resumo numérico do gráfico (texto dos Resultados)",
    ("session_report_section", "section_key"): "objetivo|introducao|informacoes_*|tendencias_ciclo_vida|conclusao|finalidade|metodologia|...",
    ("session_report_section", "rag_context"): "trechos do RAG enviados ao LLM",
    ("session_report_section", "sources"): "citações (AUTOR, ano) + entrada ABNT",
    ("session_report_section", "generated_text"): "já escapado para LaTeX",
    ("session_report", "tex_object_key"): "main.tex no MinIO (+ main.assembled.tex)",
    ("session_report", "status"): "tex_ready | complete | pdf_failed",
    ("session_report", "assemble_payload"): "capa/assinaturas/quadro - reusado no Remontar",
    ("app_settings", "key"): "ex.: rag_relative_min_relevance, languagetool_language",
    ("llm_call_site_bindings", "call_site"): "theme_candidates|probe_query|final_query|report_writing|report_review",
    ("search_api_selection", "family"): "patent | scholarly",
}

# Relacionamentos (rótulo do Mermaid) - FK -> tabela referenciada.
RELATION_LABELS: dict[tuple[str, str], str] = {
    ("session_input", "session_id"): "define",
    ("session_input", "parent_id"): "refina",
    ("session_probe_query", "session_id"): "executa",
    ("session_probe_query", "parent_id"): "refina",
    ("session_ai_call", "session_id"): "registra",
    ("probe_query_patent", "probe_query_id"): "encontra",
    ("probe_query_patent", "patent_id"): "aparece em",
    ("probe_query_article", "probe_query_id"): "encontra",
    ("probe_query_article", "article_id"): "aparece em",
    ("probe_query_term", "probe_query_id"): "extrai",
    ("session_chart", "probe_query_id"): "gera gráfico",
    ("session_report_section", "session_id"): "redige seção",
    ("session_report", "session_id"): "monta relatório",
    ("llm_call_site_bindings", "config_id"): "atende",
}

TABLE_ORDER = [
    "research_session", "session_input", "session_probe_query", "session_ai_call",
    "patent", "article", "probe_query_patent", "probe_query_article", "probe_query_term",
    "session_chart", "session_report_section", "session_report",
    "app_settings", "llm_provider_configs", "llm_call_site_bindings", "search_api_selection",
]

OBSERVATIONS = """## Observações importantes

Este banco **não é um esquema único** — são quatro grupos de tabelas que coexistem no código:

| # | Grupo | Arquivo | Situação |
|---|-------|---------|----------|
| 1 | **Sessão de prospecção** (`research_session` → `session_input`, `session_probe_query`, `session_ai_call`, `patent`, `article`, `probe_query_*`, `session_chart`, `session_report_section`, `session_report`) | `db/research_session_models.py` | **Ativo** — gerenciado via Alembic (`alembic upgrade head`). |
| 2 | **Documentos genéricos** (`scholarly_documents`, `patent_documents`, `*_dedup_registry`) | `db/models.py` | Legado, usado pelos adapters de persistência antigos; sem FK para o grupo 1. Fora do diagrama. |
| 3 | **Research legado** (`research`, `research_*`) | `db/research_models.py` | Desenho anterior ao modelo session-centric. Fora do diagrama. |
| 4 | **Configuração editável** (`app_settings`, `llm_provider_configs`, `llm_call_site_bindings`, `search_api_selection`) | `db/config_models.py` | Ativo — criado por `create_all` e populado por `db/config_seed.py` (idempotente: `seed_missing_app_settings`/`seed_missing_call_site_bindings` completam bancos existentes). |

Pontos do schema ativo (grupo 1):
- `session_input.parent_id` e `session_probe_query.parent_id` são auto-relacionamentos: a linha raiz é o input/probe, a filha é o refino/query final (`tipo = specific|balanced|generic`). UK de `session_probe_query`: `session_id + fonte + tipo`.
- `patent`/`article` são deduplicados globalmente — a mesma patente encontrada por duas queries gera **uma** linha em `patent` e **duas** em `probe_query_patent`.
- `probe_query_term` guarda os termos extraídos por NLP local (padrões gramaticais + BM25F + KeyBERT, fundidos por RRF) de uma probe query; `selected` marca os escolhidos para a query final.
- `session_chart`: um PNG por (query final, tipo de gráfico) no MinIO. `summary` (JSON) guarda o resumo numérico calculado das mesmas contagens do desenho — é o que o LLM recebe para comentar a figura nos Resultados; na curva S inclui os anos GP/MP/SP usados para o estágio do ciclo de vida.
- `session_report_section`: uma linha por seção do relatório. Seções de IA passam por `rag_context` → `generated_text`; `sources` guarda as citações (AUTOR, ano) dos documentos recuperados, usadas para validar o texto e gerar as Referências. Finalidade, Objetivo escrito pelo usuário, Metodologia e Referências Bibliográficas são gravadas pela rota de seções estáticas.
- `session_report`: o `.tex` montado (`tex_object_key`), o PDF (`pdf_object_key`) e o `assemble_payload` (capa, assinaturas `nome/posto/funcao`, quadro de busca com o total real) reaproveitado pelo "Remontar .tex". Uma cópia da versão montada (`main.assembled.tex`, no MinIO) serve de referência para a revisão detectar as edições do usuário.
- Anexos do editor ficam só no MinIO (`sessions/{id}/report/attachments/`), sem tabela.
"""


def _tables():
    tables = {t.name: t for base in (session_models.Base, config_models.Base) for t in base.metadata.sorted_tables}
    return [tables[name] for name in TABLE_ORDER if name in tables] + [
        t for name, t in tables.items() if name not in TABLE_ORDER
    ]


def _type_name(column) -> str:
    raw = str(column.type).lower()
    for prefix, name in (("varchar", "varchar"), ("text", "text"), ("integer", "integer"), ("float", "float"),
                         ("boolean", "boolean"), ("datetime", "datetime"), ("json", "json")):
        if raw.startswith(prefix):
            return name
    return raw


def _mermaid_type(column) -> str:
    return {"varchar": "String", "text": "Text", "integer": "Int", "float": "Float", "boolean": "Boolean",
            "datetime": "DateTime", "json": "JSON"}.get(_type_name(column), "String")


def _composite_uniques(table) -> list[list[str]]:
    return [
        [c.name for c in con.columns]
        for con in table.constraints
        if con.__class__.__name__ == "UniqueConstraint" and len(con.columns) > 1
    ]


def _foreign_keys(table):
    for column in table.columns:
        for fk in column.foreign_keys:
            yield column.name, fk.column.table.name, fk.column.name


def build_dbml() -> str:
    lines = [
        "// Diagrama do Banco de Dados — Prospecção Tecnológica (PFC)",
        "// GERADO por scripts/generate_db_schema_docs.py a partir dos modelos SQLAlchemy - não editar à mão.",
        "// Grupo 1 (sessão, db/research_session_models.py) + Grupo 4 (configuração, db/config_models.py).",
        "// Cole em https://dbdiagram.io/home (New Diagram > cole no editor DBML).",
        "",
    ]
    refs = []
    for table in _tables():
        lines.append(f"Table {table.name} {{")
        for column in table.columns:
            attrs = []
            if column.primary_key:
                attrs.append("pk")
            if column.unique:
                attrs.append("unique")
            if not column.nullable and not column.primary_key:
                attrs.append("not null")
            note = COLUMN_NOTES.get((table.name, column.name))
            if note:
                attrs.append(f'note: "{note}"')
            suffix = f" [{', '.join(attrs)}]" if attrs else ""
            lines.append(f"  {column.name} {_type_name(column)}{suffix}")
        uniques = _composite_uniques(table)
        if uniques:
            lines.append("")
            lines.append("  indexes {")
            for cols in uniques:
                lines.append(f"    ({', '.join(cols)}) [unique]")
            lines.append("  }")
        lines.append("}")
        lines.append("")
        for column_name, ref_table, ref_column in _foreign_keys(table):
            refs.append(f"Ref: {table.name}.{column_name} > {ref_table}.{ref_column}")
    return "\n".join(lines + refs) + "\n"


def build_mermaid(indent: str = "\t") -> str:
    lines = ["erDiagram", f"{indent}direction TB"]
    relations = []
    for table in _tables():
        uniques = {c for cols in _composite_uniques(table) for c in cols}
        fks = {name for name, _, _ in _foreign_keys(table)}
        lines.append(f"{indent}{table.name} {{")
        for column in table.columns:
            key = "PK" if column.primary_key else "FK" if column.name in fks else "UK" if column.unique else ""
            note = COLUMN_NOTES.get((table.name, column.name), "")
            if column.name in uniques and not column.primary_key:
                note = f"UK composta; {note}" if note else "UK composta"
            if column.nullable and not column.primary_key:
                note = f"optional; {note}" if note else "optional"
            note = note.replace('"', "'")
            lines.append(f'{indent}{indent}{_mermaid_type(column)} {column.name} {key} "{note}"'.replace("  ", " "))
        lines.append(f"{indent}}}")
        lines.append("")
        for column_name, ref_table, _ in _foreign_keys(table):
            label = RELATION_LABELS.get((table.name, column_name), column_name)
            unique_fk = any(c.name == column_name and c.unique for c in table.columns)
            cardinality = "||--o|" if unique_fk else "||--o{"
            relations.append(f'{indent}{ref_table}{cardinality}{table.name}:"{label}"')
    return "\n".join(lines + relations)


def build_md() -> str:
    return (
        "# Diagrama do Banco de Dados — Prospecção Tecnológica (PFC)\n\n"
        "> Gerado por `scripts/generate_db_schema_docs.py` a partir dos modelos SQLAlchemy — não editar à mão.\n\n"
        "## Como visualizar\n\n"
        "### Opção 1 — mermaid.live (sem instalar nada)\n"
        "1. Acesse **https://mermaid.live**\n"
        "2. Apague o conteúdo do painel esquerdo\n"
        "3. Cole o bloco Mermaid abaixo (sem os três backticks)\n"
        "4. O diagrama aparece ao vivo no painel direito\n\n"
        "### Opção 2 — VS Code\n"
        "Instale a extensão **Markdown Preview Mermaid Support** (`bierner.markdown-mermaid`) e pressione "
        "`Ctrl+Shift+V` neste arquivo.\n\n"
        "---\n\n"
        f"```mermaid\n{build_mermaid()}\n```\n\n"
        "---\n\n"
        f"{OBSERVATIONS}"
    )


def build_html(previous_html: str) -> str:
    """Reaproveita o wrapper (estilo + renderização Mermaid) do HTML atual e
    troca só a introdução e o diagrama."""
    head, _, rest = previous_html.partition("const diagram = `")
    _, _, tail = rest.partition("`;")
    intro_start = head.index("<p ")
    intro_end = head.index("</p>") + len("</p>")
    intro = (
        '<p style="font-size:13px;color:#73726c;max-width:860px;margin:0 0 12px;">\n'
        "  Esquema ativo: <strong>sessão de prospecção</strong> (<code>db/research_session_models.py</code>, "
        "migrado via Alembic) e <strong>configuração editável</strong> (<code>db/config_models.py</code>). "
        "Inclui os gráficos do relatório (<code>session_chart</code>, com o resumo numérico em <code>summary</code>), "
        "as seções redigidas (<code>session_report_section</code>, com as citações em <code>sources</code>) e o "
        "documento montado (<code>session_report</code>). Gerado por "
        "<code>scripts/generate_db_schema_docs.py</code>.\n</p>"
    )
    head = head[:intro_start] + intro + head[intro_end:]
    diagram = build_mermaid(indent="  ").replace("`", "'")
    return f"{head}const diagram = `{diagram}\n`;{tail}"


def main() -> None:
    html_path = NOTES_DIR / "db_schema_atual.html"
    previous_html = html_path.read_text(encoding="utf-8")
    (NOTES_DIR / "db_schema_atual.dbml").write_text(build_dbml(), encoding="utf-8", newline="\n")
    (NOTES_DIR / "db_schema_atual.md").write_text(build_md(), encoding="utf-8", newline="\n")
    html_path.write_text(build_html(previous_html), encoding="utf-8", newline="\n")
    print("db_schema_atual.{dbml,md,html} gerados em", NOTES_DIR)


if __name__ == "__main__":
    main()
