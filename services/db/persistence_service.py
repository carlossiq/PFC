"""
Persistence service for storing normalized and filtered documents.

Orchestrates the persistence pipeline:
1. Relevance filtering (input)
2. Deduplication (repository check)
3. Metadata normalization (input)
4. Database storage (this service)
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from schemas.normalized_metadata import (
    StandardizedPatentMetadata,
    StandardizedScholarlyMetadata,
)
from services.db.repositories import (
    DedupRegistry,
    PatentDocumentRepository,
    ScholarlyDocumentRepository,
)

logger = get_logger(__name__)


class PersistenceService:
    """
    Serviço de persistência de documentos.

    Aceita documentos já filtrados, dedupados e normalizados,
    e os persiste em banco de dados.

    Fluxo esperado:
    1. Relevance filtering (RelevanceService)
    2. Deduplication (DedupService)
    3. Metadata normalization (NormalizationService)
    4. Persistence (este serviço)
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o serviço de persistência.

        Args:
            session: Sessão assíncrona do SQLAlchemy.
        """
        self.session = session
        self.scholarly_repo = ScholarlyDocumentRepository(session)
        self.patent_repo = PatentDocumentRepository(session)
        self.dedup_registry = DedupRegistry(session)

    async def persist_scholarly(
        self,
        metadata: StandardizedScholarlyMetadata,
        skip_if_exists: bool = True,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Persiste publicação acadêmica normalizada e filtrada.

        Assume que documento já foi:
        - Filtrado por relevância
        - Dedupado (não há duplicata no banco)
        - Normalizado

        Args:
            metadata: Metadados normalizados já filtrados.
            skip_if_exists: Se True, não atualiza se já existe.
            run_id: ID único da requisição para logging.

        Returns:
            Dict com resultado da persistência.
        """
        logger.info(
            "scholarly_persistence_started",
            dedup_key=metadata.dedup_key,
            source=metadata.source,
            run_id=run_id,
        )

        try:
            # Verificar se já existe
            existing = await self.scholarly_repo.get_by_dedup_key(metadata.dedup_key)

            if existing:
                logger.info(
                    "scholarly_document_already_exists",
                    dedup_key=metadata.dedup_key,
                    document_id=existing.id,
                    run_id=run_id,
                )

                if skip_if_exists:
                    return {
                        "success": True,
                        "action": "skipped_exists",
                        "document_id": existing.id,
                        "dedup_key": metadata.dedup_key,
                    }

                # Atualizar se não skip
                updated = await self.scholarly_repo.update(metadata.dedup_key, metadata)

                return {
                    "success": True,
                    "action": "updated",
                    "document_id": updated.id,
                    "dedup_key": metadata.dedup_key,
                }

            # Criar novo
            doc = await self.scholarly_repo.create(metadata)

            # Registrar em dedup registry
            await self.dedup_registry.register_scholarly(
                dedup_key=metadata.dedup_key,
                document_id=doc.id,
                source=metadata.source,
                source_record_id=metadata.source_record_id,
            )

            logger.info(
                "scholarly_document_persisted",
                document_id=doc.id,
                dedup_key=metadata.dedup_key,
                run_id=run_id,
            )

            return {
                "success": True,
                "action": "created",
                "document_id": doc.id,
                "dedup_key": metadata.dedup_key,
            }

        except Exception as exc:
            logger.error(
                "scholarly_persistence_error",
                error=str(exc),
                dedup_key=metadata.dedup_key,
                run_id=run_id,
            )
            raise

    async def persist_patent(
        self,
        metadata: StandardizedPatentMetadata,
        skip_if_exists: bool = True,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Persiste patente normalizada e filtrada.

        Assume que documento já foi:
        - Filtrado por relevância
        - Dedupado (não há duplicata no banco)
        - Normalizado

        Args:
            metadata: Metadados normalizados já filtrados.
            skip_if_exists: Se True, não atualiza se já existe.
            run_id: ID único da requisição para logging.

        Returns:
            Dict com resultado da persistência.
        """
        logger.info(
            "patent_persistence_started",
            dedup_key=metadata.dedup_key,
            source=metadata.source,
            run_id=run_id,
        )

        try:
            # Verificar se já existe
            existing = await self.patent_repo.get_by_dedup_key(metadata.dedup_key)

            if existing:
                logger.info(
                    "patent_document_already_exists",
                    dedup_key=metadata.dedup_key,
                    document_id=existing.id,
                    run_id=run_id,
                )

                if skip_if_exists:
                    return {
                        "success": True,
                        "action": "skipped_exists",
                        "document_id": existing.id,
                        "dedup_key": metadata.dedup_key,
                    }

                # Atualizar se não skip
                updated = await self.patent_repo.update(metadata.dedup_key, metadata)

                return {
                    "success": True,
                    "action": "updated",
                    "document_id": updated.id,
                    "dedup_key": metadata.dedup_key,
                }

            # Criar novo
            doc = await self.patent_repo.create(metadata)

            # Registrar em dedup registry
            await self.dedup_registry.register_patent(
                dedup_key=metadata.dedup_key,
                document_id=doc.id,
                source=metadata.source,
                source_record_id=metadata.source_record_id,
            )

            logger.info(
                "patent_document_persisted",
                document_id=doc.id,
                dedup_key=metadata.dedup_key,
                run_id=run_id,
            )

            return {
                "success": True,
                "action": "created",
                "document_id": doc.id,
                "dedup_key": metadata.dedup_key,
            }

        except Exception as exc:
            logger.error(
                "patent_persistence_error",
                error=str(exc),
                dedup_key=metadata.dedup_key,
                run_id=run_id,
            )
            raise

    async def persist_batch_scholarly(
        self,
        metadata_list: list[StandardizedScholarlyMetadata],
        skip_if_exists: bool = True,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Persiste lote de publicações.

        Args:
            metadata_list: Lista de metadados normalizados.
            skip_if_exists: Se True, não atualiza existentes.
            run_id: ID da requisição.

        Returns:
            Dict com resumo da persistência.
        """
        results = {
            "total": len(metadata_list),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "documents": [],
        }

        for metadata in metadata_list:
            try:
                result = await self.persist_scholarly(metadata, skip_if_exists, run_id)
                results["documents"].append(result)

                if result["action"] == "created":
                    results["created"] += 1
                elif result["action"] == "updated":
                    results["updated"] += 1
                elif result["action"] == "skipped_exists":
                    results["skipped"] += 1

            except Exception as exc:
                logger.error(
                    "batch_scholarly_item_error",
                    error=str(exc),
                    dedup_key=metadata.dedup_key,
                )
                results["failed"] += 1

        logger.info(
            "batch_scholarly_persistence_complete",
            total=results["total"],
            created=results["created"],
            updated=results["updated"],
            skipped=results["skipped"],
            failed=results["failed"],
            run_id=run_id,
        )

        # Commit após lote completo
        # TODO: Decidir estratégia final de commit:
        # - Por documento (transação isolada, lentos)
        # - Por lote (transação única, rápido, menos granular)
        # - Com checkpoints (compromisso entre dois)
        try:
            await self.session.commit()
            results["success"] = True
        except Exception as exc:
            await self.session.rollback()
            results["success"] = False
            results["commit_error"] = str(exc)

        return results

    async def persist_batch_patent(
        self,
        metadata_list: list[StandardizedPatentMetadata],
        skip_if_exists: bool = True,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Persiste lote de patentes.

        Args:
            metadata_list: Lista de metadados normalizados.
            skip_if_exists: Se True, não atualiza existentes.
            run_id: ID da requisição.

        Returns:
            Dict com resumo da persistência.
        """
        results = {
            "total": len(metadata_list),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "documents": [],
        }

        for metadata in metadata_list:
            try:
                result = await self.persist_patent(metadata, skip_if_exists, run_id)
                results["documents"].append(result)

                if result["action"] == "created":
                    results["created"] += 1
                elif result["action"] == "updated":
                    results["updated"] += 1
                elif result["action"] == "skipped_exists":
                    results["skipped"] += 1

            except Exception as exc:
                logger.error(
                    "batch_patent_item_error",
                    error=str(exc),
                    dedup_key=metadata.dedup_key,
                )
                results["failed"] += 1

        logger.info(
            "batch_patent_persistence_complete",
            total=results["total"],
            created=results["created"],
            updated=results["updated"],
            skipped=results["skipped"],
            failed=results["failed"],
            run_id=run_id,
        )

        # Commit após lote completo
        # TODO: Decidir estratégia final de commit (vide comentário acima)
        try:
            await self.session.commit()
            results["success"] = True
        except Exception as exc:
            await self.session.rollback()
            results["success"] = False
            results["commit_error"] = str(exc)

        return results
