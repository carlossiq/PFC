from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


class DedupService:
    """
    Deduplicação de documentos usando chaves primárias com fallback
    para título normalizado + ano.
    """

    def deduplicate_patents(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []

        for doc in documents:
            key = self._get_patent_dedup_key(doc)
            if key not in seen:
                seen.add(key)
                unique.append(doc)
            else:
                duplicates.append(doc)

        logger.info(
            "patents_deduplicated total=%d unique=%d duplicates=%d",
            len(documents),
            len(unique),
            len(duplicates),
        )
        return unique, duplicates

    def deduplicate_scholarly(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []

        for doc in documents:
            key = self._get_scholarly_dedup_key(doc)
            if key not in seen:
                seen.add(key)
                unique.append(doc)
            else:
                duplicates.append(doc)

        logger.info(
            "scholarly_deduplicated total=%d unique=%d duplicates=%d",
            len(documents),
            len(unique),
            len(duplicates),
        )
        return unique, duplicates

    def deduplicate_mixed(
        self,
        patent_docs: list[dict[str, Any]],
        scholarly_docs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        unique_patents, dup_patents = self.deduplicate_patents(patent_docs)
        unique_scholarly, dup_scholarly = self.deduplicate_scholarly(scholarly_docs)
        return {
            "unique_patents": unique_patents,
            "unique_scholarly": unique_scholarly,
            "duplicate_patents": dup_patents,
            "duplicate_scholarly": dup_scholarly,
        }

    def merge_duplicates(
        self,
        documents: list[dict[str, Any]],
        document_type: str,
    ) -> list[dict[str, Any]]:
        if document_type == "patent":
            unique, _ = self.deduplicate_patents(documents)
        elif document_type == "scholarly":
            unique, _ = self.deduplicate_scholarly(documents)
        else:
            raise ValueError(f"Unknown document type: {document_type}")

        logger.info(
            "duplicates_merged type=%s original=%d merged=%d",
            document_type,
            len(documents),
            len(unique),
        )
        return unique

    def create_dedup_key(self, document_type: str, **kwargs: Any) -> str:
        doc = dict(kwargs)
        if document_type == "patent":
            return self._get_patent_dedup_key(doc)
        elif document_type == "scholarly":
            return self._get_scholarly_dedup_key(doc)
        raise ValueError(f"Unknown document type: {document_type}")

    def _get_patent_dedup_key(self, doc: dict[str, Any]) -> str:
        pub_num = doc.get("publication_number")
        if pub_num:
            return f"patent:{pub_num}"

        title = self._normalize_text(doc.get("title", ""))
        year = doc.get("year", "unknown")
        if title:
            return f"patent:{title}:{year}"

        return f"patent:{doc.get('source_record_id', 'unknown')}"

    def _get_scholarly_dedup_key(self, doc: dict[str, Any]) -> str:
        doi = doc.get("doi")
        if doi:
            return f"scholarly:{doi.lower()}"

        title = self._normalize_text(doc.get("title", ""))
        year = doc.get("year", "unknown")
        if title:
            return f"scholarly:{title}:{year}"

        return f"scholarly:{doc.get('source_record_id', 'unknown')}"

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = "".join(
            c
            for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return " ".join(text.split())
