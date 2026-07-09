from __future__ import annotations

from db.models import PatentDocument, ScholarlyDocument
from schemas.normalized_metadata import (
    StandardizedPatentMetadata,
    StandardizedScholarlyMetadata,
)


def scholarly_doc_to_metadata(doc: ScholarlyDocument) -> StandardizedScholarlyMetadata:
    return StandardizedScholarlyMetadata(
        source=doc.source,
        source_record_id=doc.source_record_id,
        dedup_key=doc.dedup_key,
        title=doc.title,
        abstract=doc.abstract,
        doi=doc.doi,
        authors=doc.authors or [],
        affiliations=doc.affiliations or [],
        journal_or_source=doc.journal_or_source,
        volume=doc.volume,
        issue=doc.issue,
        pages=doc.pages,
        publication_date=doc.publication_date,
        year=doc.year,
        keywords=doc.keywords or [],
        field_of_study=doc.field_of_study or [],
        citations=doc.citations,
        relevance_score=doc.relevance_score,
        raw_payload=doc.raw_payload,
        created_at=doc.created_at,
    )


def patent_doc_to_metadata(doc: PatentDocument) -> StandardizedPatentMetadata:
    return StandardizedPatentMetadata(
        source=doc.source,
        source_record_id=doc.source_record_id,
        dedup_key=doc.dedup_key,
        title=doc.title,
        abstract=doc.abstract,
        publication_number=doc.publication_number,
        application_number=doc.application_number,
        family_id=doc.family_id,
        applicants=doc.applicants or [],
        inventors=doc.inventors or [],
        ipc_codes=doc.ipc_codes or [],
        cpc_codes=doc.cpc_codes or [],
        filing_date=doc.filing_date,
        publication_date=doc.publication_date,
        grant_date=doc.grant_date,
        year=doc.year,
        legal_status=doc.legal_status,
        relevance_score=doc.relevance_score,
        raw_payload=doc.raw_payload,
        created_at=doc.created_at,
    )
