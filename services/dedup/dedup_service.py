"""
Deduplication service for identifying and removing duplicate documents.
"""

import re
import unicodedata
from typing import Any, Optional

from core.logging import get_logger

logger = get_logger(__name__)


class DedupService:
    """
    Serviço de deduplicação de documentos.

    Identifica documentos duplicados de múltiplas fontes usando
    estratégia de chaves primárias e fallback.
    """

    def __init__(self) -> None:
        """
        Inicializa o serviço de deduplicação.
        """
        pass

    def deduplicate_patents(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Deduplica patentes.

        Usar publication_number como chave primária,
        fallback para normalized_title + year.

        Args:
            documents: Lista de patentes com campos padronizados.

        Returns:
            Tuple (documents_unicos, documentos_duplicados).
        """
        seen_keys = set()
        unique_docs = []
        duplicate_docs = []

        for doc in documents:
            # Gerar chave de deduplicação
            dedup_key = self._get_patent_dedup_key(doc)

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                unique_docs.append(doc)
            else:
                duplicate_docs.append(doc)

        logger.info(
            "patents_deduplicated",
            total_count=len(documents),
            unique_count=len(unique_docs),
            duplicate_count=len(duplicate_docs),
        )

        return unique_docs, duplicate_docs

    def deduplicate_scholarly(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Deduplica publicações acadêmicas.

        Usar DOI como chave primária, fallback para
        normalized_title + year.

        Args:
            documents: Lista de publicações com campos padronizados.

        Returns:
            Tuple (documents_unicos, documentos_duplicados).
        """
        seen_keys = set()
        unique_docs = []
        duplicate_docs = []

        for doc in documents:
            # Gerar chave de deduplicação
            dedup_key = self._get_scholarly_dedup_key(doc)

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                unique_docs.append(doc)
            else:
                duplicate_docs.append(doc)

        logger.info(
            "scholarly_deduplicated",
            total_count=len(documents),
            unique_count=len(unique_docs),
            duplicate_count=len(duplicate_docs),
        )

        return unique_docs, duplicate_docs

    def deduplicate_mixed(
        self,
        patent_docs: list[dict[str, Any]],
        scholarly_docs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Deduplica documentos de tipos diferentes.

        Args:
            patent_docs: Patentes.
            scholarly_docs: Publicações acadêmicas.

        Returns:
            Dict com:
            - unique_patents
            - unique_scholarly
            - duplicate_patents
            - duplicate_scholarly
        """
        unique_patents, dup_patents = self.deduplicate_patents(patent_docs)
        unique_scholarly, dup_scholarly = self.deduplicate_scholarly(scholarly_docs)

        return {
            "unique_patents": unique_patents,
            "unique_scholarly": unique_scholarly,
            "duplicate_patents": dup_patents,
            "duplicate_scholarly": dup_scholarly,
        }

    def _get_patent_dedup_key(self, doc: dict[str, Any]) -> str:
        """
        Gera chave de deduplicação para patente.

        Estratégia:
        1. Usar publication_number se disponível
        2. Fallback: normalized_title + year

        Args:
            doc: Documento de patente.

        Returns:
            Chave única de deduplicação.
        """
        # Chave primária
        publication_number = doc.get("publication_number")
        if publication_number:
            return f"patent:{publication_number}"

        # Fallback
        title = doc.get("title", "")
        year = doc.get("year", "unknown")

        normalized_title = self._normalize_text(title)

        if normalized_title:
            return f"patent:{normalized_title}:{year}"

        # Último recurso: usar source_record_id
        source_record_id = doc.get("source_record_id", "unknown")
        return f"patent:{source_record_id}"

    def _get_scholarly_dedup_key(self, doc: dict[str, Any]) -> str:
        """
        Gera chave de deduplicação para publicação acadêmica.

        Estratégia:
        1. Usar DOI se disponível
        2. Fallback: normalized_title + year

        Args:
            doc: Documento de publicação.

        Returns:
            Chave única de deduplicação.
        """
        # Chave primária
        doi = doc.get("doi")
        if doi:
            return f"scholarly:{doi.lower()}"

        # Fallback
        title = doc.get("title", "")
        year = doc.get("year", "unknown")

        normalized_title = self._normalize_text(title)

        if normalized_title:
            return f"scholarly:{normalized_title}:{year}"

        # Último recurso
        source_record_id = doc.get("source_record_id", "unknown")
        return f"scholarly:{source_record_id}"

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normaliza texto para comparação.

        Remove acentos, converte para lowercase,
        remove caracteres especiais.

        Args:
            text: Texto a normalizar.

        Returns:
            Texto normalizado.
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remover acentos
        text = "".join(
            c
            for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )

        # Remover caracteres especiais mantendo espaços
        text = re.sub(r"[^a-z0-9\s]", "", text)

        # Normalizar espaços
        text = " ".join(text.split())

        return text

    def create_dedup_key(
        self,
        document_type: str,
        **kwargs,
    ) -> str:
        """
        Cria chave de deduplicação genérica.

        Args:
            document_type: 'patent' ou 'scholarly'.
            **kwargs: Campos do documento.

        Returns:
            Chave de deduplicação.
        """
        doc = dict(kwargs)

        if document_type == "patent":
            return self._get_patent_dedup_key(doc)
        elif document_type == "scholarly":
            return self._get_scholarly_dedup_key(doc)
        else:
            raise ValueError(f"Unknown document type: {document_type}")

    def merge_duplicates(
        self,
        documents: list[dict[str, Any]],
        document_type: str,
    ) -> list[dict[str, Any]]:
        """
        Mescla documentos duplicados preservando informações.

        Estratégia: manter documento com mais campos preenchidos,
        agregar listas (authors, keywords, etc).

        Args:
            documents: Lista que pode conter duplicatas.
            document_type: 'patent' ou 'scholarly'.

        Returns:
            Lista com duplicatas mescladas.
        """
        if document_type == "patent":
            unique, _ = self.deduplicate_patents(documents)
        elif document_type == "scholarly":
            unique, _ = self.deduplicate_scholarly(documents)
        else:
            raise ValueError(f"Unknown document type: {document_type}")

        # TODO: Implementar lógica de merge mais sofisticada
        # - Agregar campos de lista (authors, keywords, codes, etc)
        # - Manter informação com mais confiança
        # - Registrar origem de cada campo

        logger.info(
            "duplicates_merged",
            document_type=document_type,
            original_count=len(documents),
            merged_count=len(unique),
        )

        return unique
