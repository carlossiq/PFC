"""
Mapeia os dicts crus de resultado de probe search (OPS/Scopus, como devolvidos
por ChatService.run_probe_search) para as colunas de Patent/Article, e
sincroniza os links dessas tabelas com uma SessionProbeQuery.

O mapeamento campo-a-campo em si vive em NormalizationService
(services/db/normalization_service.py) - aqui só convertemos o
StandardizedPatentMetadata/StandardizedScholarlyMetadata resultante pras
colunas ORM e cuidamos do upsert/sync (que não é responsabilidade do
normalizer).
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.research_session_models import Article, Patent, ProbeQueryArticle, ProbeQueryPatent, SessionProbeQuery
from services.db.normalization_service import NormalizationService

_normalizer = NormalizationService()


def build_patent_fields(item: dict[str, Any]) -> dict[str, Any]:
    metadata = _normalizer.normalize_from_ops(item)
    return dict(
        dedup_key=metadata.dedup_key,
        source=metadata.source,
        source_record_id=metadata.source_record_id or None,
        title=metadata.title or "Sem título",
        abstract=metadata.abstract,
        publication_number=metadata.publication_number,
        application_number=metadata.application_number,
        family_id=metadata.family_id,
        applicants=metadata.applicants or None,
        inventors=metadata.inventors or None,
        ipc_codes=metadata.ipc_codes or None,
        cpc_codes=metadata.cpc_codes or None,
        filing_date=metadata.filing_date,
        publication_date=metadata.publication_date,
        grant_date=metadata.grant_date,
        year=metadata.year,
        legal_status=metadata.legal_status,
        country=metadata.country,
    )


def build_article_fields(item: dict[str, Any]) -> dict[str, Any]:
    metadata = _normalizer.normalize_from_scopus(item)
    return dict(
        dedup_key=metadata.dedup_key,
        source=metadata.source,
        source_record_id=metadata.source_record_id or None,
        title=metadata.title or "Sem título",
        abstract=metadata.abstract,
        doi=metadata.doi,
        authors=metadata.authors or None,
        affiliations=metadata.affiliations or None,
        affiliation_countries=metadata.affiliation_countries or None,
        journal_or_source=metadata.journal_or_source,
        volume=metadata.volume,
        issue=metadata.issue,
        pages=metadata.pages,
        publication_date=metadata.publication_date,
        year=metadata.year,
        keywords=metadata.keywords or None,
        field_of_study=metadata.field_of_study or None,
        citations=metadata.citations,
    )


async def _upsert_by_dedup_key(
    session: AsyncSession,
    model: type,
    field_dicts: list[dict[str, Any]],
) -> list[Any]:
    """Busca linhas existentes por dedup_key (1 select em lote), atualiza os
    campos em quem já existe, cria as que faltam. Sobrescrita total dos
    campos (mesmo espírito de apply_probe_query_fields), não diff por campo."""
    if not field_dicts:
        return []

    keys = [fields["dedup_key"] for fields in field_dicts]
    existing = (
        (await session.execute(select(model).where(model.dedup_key.in_(keys)))).scalars().all()
    )
    by_key = {row.dedup_key: row for row in existing}

    rows = []
    for fields in field_dicts:
        row = by_key.get(fields["dedup_key"])
        if row is None:
            row = model(**fields)
            session.add(row)
            by_key[fields["dedup_key"]] = row
        else:
            for key, value in fields.items():
                setattr(row, key, value)
        rows.append(row)

    await session.flush()
    return rows


def patent_to_raw_item(patent: Patent) -> dict[str, Any]:
    """
    Inverso de build_patent_fields - reconstrói um dict no formato "cru" (as
    chaves que o probe search da OPS devolveria) a partir de uma linha Patent
    já persistida. Usado ao retomar uma sessão salva, pra popular de volta
    step3PatentResults no frontend sem precisar rebuscar na OPS - e, como o
    resultado é reconstruído com os MESMOS campos usados por build_patent_fields,
    ele recalcula o mesmo dedup_key se for salvo de novo (não duplica a linha).
    """
    return {
        "invention_title": patent.title,
        "abstract": patent.abstract,
        "publication_date": patent.publication_date,
        "applicants": patent.applicants or [],
        "inventors": patent.inventors or [],
        "ipc_classifications": patent.ipc_codes or [],
        "cpc_classifications": patent.cpc_codes or [],
        "docdb_id": patent.publication_number,
        "application_reference": patent.application_number,
        "family_id": patent.family_id,
        "country": patent.country,
    }


def article_to_raw_item(article: Article) -> dict[str, Any]:
    """Ver patent_to_raw_item - mesma ideia, inverso de build_article_fields."""
    return {
        "dc:title": article.title,
        "dc:description": article.abstract,
        "prism:doi": article.doi,
        "dc:creator": article.authors[0] if article.authors else None,
        "prism:publicationName": article.journal_or_source,
        "prism:volume": article.volume,
        "prism:issueIdentifier": article.issue,
        "prism:pageRange": article.pages,
        "prism:coverDate": article.publication_date,
        "citedby-count": str(article.citations) if article.citations is not None else None,
        "openalex_field_of_study": article.field_of_study or [],
        "affiliation": [{"affiliation-country": c} for c in (article.affiliation_countries or [])],
    }


async def sync_probe_query_patents(
    session: AsyncSession,
    probe_query: SessionProbeQuery,
    raw_items: list[dict[str, Any]],
) -> None:
    """Sincroniza os patentes encontrados por uma probe query - replace
    completo dos links (remove os que saíram do conjunto atual, adiciona os
    novos), já que o conjunto encontrado pode mudar entre regenerações.

    Consulta ProbeQueryPatent diretamente (em vez de acessar
    probe_query.patent_links) porque, num registro de SessionProbeQuery recém
    criado nesta mesma transação, a relationship ainda não foi carregada e um
    acesso a ela dispararia lazy-load - proibido em SQLAlchemy async
    (MissingGreenlet)."""
    field_dicts = [build_patent_fields(item) for item in raw_items]
    patents = await _upsert_by_dedup_key(session, Patent, field_dicts)

    existing_links = (
        (
            await session.execute(
                select(ProbeQueryPatent).where(ProbeQueryPatent.probe_query_id == probe_query.id)
            )
        )
        .scalars()
        .all()
    )
    existing_by_patent_id = {link.patent_id: link for link in existing_links}
    wanted_ids = {patent.id for patent in patents}

    for patent_id, link in existing_by_patent_id.items():
        if patent_id not in wanted_ids:
            await session.delete(link)

    for patent in patents:
        if patent.id not in existing_by_patent_id:
            session.add(ProbeQueryPatent(probe_query_id=probe_query.id, patent_id=patent.id))


async def sync_probe_query_articles(
    session: AsyncSession,
    probe_query: SessionProbeQuery,
    raw_items: list[dict[str, Any]],
) -> None:
    """Ver sync_probe_query_patents - mesma lógica, pro lado de artigos."""
    field_dicts = [build_article_fields(item) for item in raw_items]
    articles = await _upsert_by_dedup_key(session, Article, field_dicts)

    existing_links = (
        (
            await session.execute(
                select(ProbeQueryArticle).where(ProbeQueryArticle.probe_query_id == probe_query.id)
            )
        )
        .scalars()
        .all()
    )
    existing_by_article_id = {link.article_id: link for link in existing_links}
    wanted_ids = {article.id for article in articles}

    for article_id, link in existing_by_article_id.items():
        if article_id not in wanted_ids:
            await session.delete(link)

    for article in articles:
        if article.id not in existing_by_article_id:
            session.add(ProbeQueryArticle(probe_query_id=probe_query.id, article_id=article.id))
