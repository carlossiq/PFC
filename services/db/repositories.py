"""
Repository layer for database operations.

Handles CRUD operations for documents and dedup registries.
Separated from service layer for clean architecture.
"""

from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import (
    PatentDedupRegistry,
    PatentDocument,
    ScholarlyDedupRegistry,
    ScholarlyDocument,
)
from schemas.normalized_metadata import (
    StandardizedPatentMetadata,
    StandardizedScholarlyMetadata,
)

logger = get_logger(__name__)


class ScholarlyDocumentRepository:
    """
    Repositório para operações de publicações acadêmicas.

    Fornece interface CRUD para ScholarlyDocument.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o repositório.

        Args:
            session: Sessão assíncrona do SQLAlchemy.
        """
        self.session = session

    async def create(
        self,
        metadata: StandardizedScholarlyMetadata,
    ) -> ScholarlyDocument:
        """
        Cria novo registro de publicação.

        Args:
            metadata: Metadados normalizados.

        Returns:
            Documento criado.
        """
        doc = ScholarlyDocument(
            source=metadata.source,
            source_record_id=metadata.source_record_id,
            dedup_key=metadata.dedup_key,
            title=metadata.title,
            abstract=metadata.abstract,
            doi=metadata.doi,
            authors=metadata.authors,
            affiliations=metadata.affiliations,
            journal_or_source=metadata.journal_or_source,
            volume=metadata.volume,
            issue=metadata.issue,
            pages=metadata.pages,
            publication_date=metadata.publication_date,
            year=metadata.year,
            keywords=metadata.keywords,
            field_of_study=metadata.field_of_study,
            citations=metadata.citations,
            relevance_score=metadata.relevance_score,
            raw_payload=metadata.raw_payload,
        )

        self.session.add(doc)
        await self.session.flush()

        logger.info(
            "scholarly_document_created",
            id=doc.id,
            dedup_key=metadata.dedup_key,
        )

        return doc

    async def get_by_dedup_key(self, dedup_key: str) -> Optional[ScholarlyDocument]:
        """
        Obtém documento por chave de deduplicação.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            Documento ou None se não encontrado.
        """
        stmt = select(ScholarlyDocument).where(ScholarlyDocument.dedup_key == dedup_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_doi(self, doi: str) -> Optional[ScholarlyDocument]:
        """
        Obtém documento por DOI.

        Args:
            doi: Digital Object Identifier.

        Returns:
            Documento ou None.
        """
        stmt = select(ScholarlyDocument).where(ScholarlyDocument.doi == doi)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_dedup_key(self, dedup_key: str) -> bool:
        """
        Verifica se dedup_key já existe.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            True se existe.
        """
        stmt = select(ScholarlyDocument).where(
            ScholarlyDocument.dedup_key == dedup_key
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedScholarlyMetadata,
    ) -> Optional[ScholarlyDocument]:
        """
        Atualiza documento existente.

        Args:
            dedup_key: Chave do documento.
            metadata: Novos metadados.

        Returns:
            Documento atualizado ou None.
        """
        doc = await self.get_by_dedup_key(dedup_key)

        if not doc:
            return None

        # Atualizar campos
        doc.title = metadata.title
        doc.abstract = metadata.abstract
        doc.authors = metadata.authors
        doc.affiliations = metadata.affiliations
        doc.journal_or_source = metadata.journal_or_source
        doc.keywords = metadata.keywords
        doc.field_of_study = metadata.field_of_study
        doc.citations = metadata.citations
        doc.relevance_score = metadata.relevance_score

        await self.session.flush()

        logger.info("scholarly_document_updated", dedup_key=dedup_key)

        return doc

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[ScholarlyDocument]:
        """
        Obtém documentos por fonte e ano.

        Args:
            source: Fonte (scopus, lens_scholarly, etc).
            year: Ano.
            limit: Limite de resultados.

        Returns:
            Lista de documentos.
        """
        stmt = (
            select(ScholarlyDocument)
            .where(
                and_(
                    ScholarlyDocument.source == source,
                    ScholarlyDocument.year == year,
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PatentDocumentRepository:
    """
    Repositório para operações de patentes.

    Fornece interface CRUD para PatentDocument.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o repositório.

        Args:
            session: Sessão assíncrona do SQLAlchemy.
        """
        self.session = session

    async def create(
        self,
        metadata: StandardizedPatentMetadata,
    ) -> PatentDocument:
        """
        Cria novo registro de patente.

        Args:
            metadata: Metadados normalizados.

        Returns:
            Documento criado.
        """
        doc = PatentDocument(
            source=metadata.source,
            source_record_id=metadata.source_record_id,
            dedup_key=metadata.dedup_key,
            title=metadata.title,
            abstract=metadata.abstract,
            publication_number=metadata.publication_number,
            application_number=metadata.application_number,
            family_id=metadata.family_id,
            applicants=metadata.applicants,
            inventors=metadata.inventors,
            ipc_codes=metadata.ipc_codes,
            cpc_codes=metadata.cpc_codes,
            filing_date=metadata.filing_date,
            publication_date=metadata.publication_date,
            grant_date=metadata.grant_date,
            year=metadata.year,
            legal_status=metadata.legal_status,
            relevance_score=metadata.relevance_score,
            raw_payload=metadata.raw_payload,
        )

        self.session.add(doc)
        await self.session.flush()

        logger.info(
            "patent_document_created",
            id=doc.id,
            publication_number=metadata.publication_number,
        )

        return doc

    async def get_by_dedup_key(self, dedup_key: str) -> Optional[PatentDocument]:
        """
        Obtém patente por chave de deduplicação.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            Patente ou None se não encontrada.
        """
        stmt = select(PatentDocument).where(PatentDocument.dedup_key == dedup_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_publication_number(
        self,
        publication_number: str,
    ) -> Optional[PatentDocument]:
        """
        Obtém patente por número de publicação.

        Args:
            publication_number: Número de publicação.

        Returns:
            Patente ou None.
        """
        stmt = select(PatentDocument).where(
            PatentDocument.publication_number == publication_number
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_dedup_key(self, dedup_key: str) -> bool:
        """
        Verifica se dedup_key já existe.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            True se existe.
        """
        stmt = select(PatentDocument).where(
            PatentDocument.dedup_key == dedup_key
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedPatentMetadata,
    ) -> Optional[PatentDocument]:
        """
        Atualiza patente existente.

        Args:
            dedup_key: Chave da patente.
            metadata: Novos metadados.

        Returns:
            Patente atualizada ou None.
        """
        doc = await self.get_by_dedup_key(dedup_key)

        if not doc:
            return None

        # Atualizar campos
        doc.title = metadata.title
        doc.abstract = metadata.abstract
        doc.applicants = metadata.applicants
        doc.inventors = metadata.inventors
        doc.ipc_codes = metadata.ipc_codes
        doc.cpc_codes = metadata.cpc_codes
        doc.legal_status = metadata.legal_status
        doc.relevance_score = metadata.relevance_score

        await self.session.flush()

        logger.info("patent_document_updated", dedup_key=dedup_key)

        return doc

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[PatentDocument]:
        """
        Obtém patentes por fonte e ano.

        Args:
            source: Fonte (lens_patent, ops, etc).
            year: Ano.
            limit: Limite de resultados.

        Returns:
            Lista de patentes.
        """
        stmt = (
            select(PatentDocument)
            .where(
                and_(
                    PatentDocument.source == source,
                    PatentDocument.year == year,
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class DedupRegistry:
    """
    Repositório para registros de deduplicação.

    Mantém registro rápido de dedup_keys já vistos.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o repositório.

        Args:
            session: Sessão assíncrona do SQLAlchemy.
        """
        self.session = session

    async def register_scholarly(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> ScholarlyDedupRegistry:
        """
        Registra novo dedup de publicação.

        Args:
            dedup_key: Chave de dedup.
            document_id: ID do documento no banco.
            source: Fonte original.
            source_record_id: ID na fonte.

        Returns:
            Registro criado.
        """
        registry = ScholarlyDedupRegistry(
            dedup_key=dedup_key,
            document_id=document_id,
            source=source,
            source_record_ids=[source_record_id],
        )

        self.session.add(registry)
        await self.session.flush()

        return registry

    async def register_patent(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> PatentDedupRegistry:
        """
        Registra novo dedup de patente.

        Args:
            dedup_key: Chave de dedup.
            document_id: ID do documento no banco.
            source: Fonte original.
            source_record_id: ID na fonte.

        Returns:
            Registro criado.
        """
        registry = PatentDedupRegistry(
            dedup_key=dedup_key,
            document_id=document_id,
            source=source,
            source_record_ids=[source_record_id],
        )

        self.session.add(registry)
        await self.session.flush()

        return registry

    async def exists_scholarly(self, dedup_key: str) -> bool:
        """
        Verifica se dedup_key de publicação existe.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            True se existe.
        """
        stmt = select(ScholarlyDedupRegistry).where(
            ScholarlyDedupRegistry.dedup_key == dedup_key
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_patent(self, dedup_key: str) -> bool:
        """
        Verifica se dedup_key de patente existe.

        Args:
            dedup_key: Chave de dedup.

        Returns:
            True se existe.
        """
        stmt = select(PatentDedupRegistry).where(
            PatentDedupRegistry.dedup_key == dedup_key
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
