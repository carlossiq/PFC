"""
Relevance scoring and document filtering service.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from core.config import settings
from core.logging import get_logger
from services.nlp.embedding_service import EmbeddingService

logger = get_logger(__name__)


@dataclass
class DocumentRelevanceScore:
    """
    Score de relevância de um documento.

    Armazena score de similaridade e decisão de aprovação.
    """

    document_id: str
    document_title: str
    relevance_score: float
    is_approved: bool
    threshold_applied: float
    run_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Converte para dicionário.

        Returns:
            Dicionário com dados do score.
        """
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "relevance_score": round(self.relevance_score, 4),
            "is_approved": self.is_approved,
            "threshold_applied": self.threshold_applied,
            "run_id": self.run_id,
        }


@dataclass
class FilteredDocumentsResult:
    """
    Resultado da filtragem de documentos por relevância.

    Agrupa documentos aprovados e rejeitados com scores.
    """

    approved_documents: list[dict[str, Any]] = field(default_factory=list)
    rejected_documents: list[dict[str, Any]] = field(default_factory=list)
    scores: list[DocumentRelevanceScore] = field(default_factory=list)
    threshold_applied: float = 0.5
    total_documents: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    approval_rate: float = 0.0
    run_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Converte resultado para dicionário.

        Returns:
            Dicionário com filtragem e estatísticas.
        """
        return {
            "approved_documents": self.approved_documents,
            "rejected_documents": self.rejected_documents,
            "scores": [score.to_dict() for score in self.scores],
            "threshold_applied": self.threshold_applied,
            "statistics": {
                "total_documents": self.total_documents,
                "approved_count": self.approved_count,
                "rejected_count": self.rejected_count,
                "approval_rate": round(self.approval_rate, 4),
            },
            "run_id": self.run_id,
        }


class RelevanceService:
    """
    Serviço de scoring de relevância de documentos.

    Computa similaridade semântica entre tema do usuário e documentos,
    aplicando threshold para aprovação/rejeição.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None) -> None:
        """
        Inicializa o serviço de relevância.

        Args:
            embedding_service: Serviço de embeddings (cria padrão se None).
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.relevance_threshold = getattr(settings, "relevance_threshold", 0.5)

    def compute_relevance_score(
        self,
        theme_embedding: np.ndarray,
        document_embedding: np.ndarray,
    ) -> float:
        """
        Computa score de relevância entre tema e documento.

        Usa similaridade de cosseno (0 a 1).

        Args:
            theme_embedding: Embedding do tema do usuário.
            document_embedding: Embedding do documento.

        Returns:
            Score de similaridade entre 0 e 1.
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            # Garantir formato 2D
            if theme_embedding.ndim == 1:
                theme_embedding = theme_embedding.reshape(1, -1)
            if document_embedding.ndim == 1:
                document_embedding = document_embedding.reshape(1, -1)

            similarity = cosine_similarity(theme_embedding, document_embedding)[0][0]

            return float(similarity)

        except ImportError:
            logger.error("sklearn not available, using manual cosine similarity")
            return self._manual_cosine_similarity(theme_embedding, document_embedding)
        except Exception as exc:
            logger.error(f"Failed to compute relevance score: {exc}")
            return 0.0

    @staticmethod
    def _manual_cosine_similarity(
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Computa similaridade de cosseno manualmente.

        Fallback se sklearn não disponível.

        Args:
            embedding1: Primeiro embedding.
            embedding2: Segundo embedding.

        Returns:
            Score de similaridade.
        """
        if embedding1.ndim == 2:
            embedding1 = embedding1[0]
        if embedding2.ndim == 2:
            embedding2 = embedding2[0]

        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def compute_relevance_scores(
        self,
        theme: str,
        documents: list[dict[str, Any]],
        threshold: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> list[DocumentRelevanceScore]:
        """
        Computa scores de relevância para múltiplos documentos.

        Args:
            theme: Tema/query do usuário.
            documents: Lista de documentos com 'id', 'title', 'abstract', etc.
            threshold: Threshold customizado (usa config se None).
            run_id: ID único da requisição.

        Returns:
            Lista de DocumentRelevanceScore.
        """
        threshold = threshold or self.relevance_threshold

        # Gerar embedding do tema
        theme_embedding = self.embedding_service.embed_text(theme)

        if theme_embedding is None:
            logger.warning("Failed to embed theme", run_id=run_id)
            return []

        scores = []

        for doc in documents:
            # Gerar embedding do documento
            doc_embedding = self.embedding_service.embed_document(
                title=doc.get("title"),
                abstract=doc.get("abstract"),
                full_text=doc.get("full_text"),
            )

            if doc_embedding is None:
                logger.debug(f"Failed to embed document {doc.get('id')}")
                continue

            # Computar score
            relevance_score = self.compute_relevance_score(theme_embedding, doc_embedding)

            # Criar objeto de score
            score_obj = DocumentRelevanceScore(
                document_id=str(doc.get("id", "")),
                document_title=str(doc.get("title", "Unknown")),
                relevance_score=relevance_score,
                is_approved=relevance_score >= threshold,
                threshold_applied=threshold,
                run_id=run_id,
            )

            scores.append(score_obj)

        logger.info(
            "relevance_scores_computed",
            documents_count=len(documents),
            approved_count=sum(1 for s in scores if s.is_approved),
            run_id=run_id,
        )

        return scores

    def filter_documents(
        self,
        theme: str,
        documents: list[dict[str, Any]],
        threshold: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> FilteredDocumentsResult:
        """
        Filtra documentos por relevância.

        Separa documentos em aprovados (score >= threshold) e rejeitados.

        Args:
            theme: Tema/query do usuário.
            documents: Lista de documentos.
            threshold: Threshold customizado (usa config se None).
            run_id: ID único da requisição.

        Returns:
            FilteredDocumentsResult com documentos separados e scores.
        """
        threshold = threshold or self.relevance_threshold

        # Computar scores
        scores = self.compute_relevance_scores(
            theme=theme,
            documents=documents,
            threshold=threshold,
            run_id=run_id,
        )

        if not scores:
            logger.warning("No scores computed", run_id=run_id)
            return FilteredDocumentsResult(
                threshold_applied=threshold,
                total_documents=len(documents),
                run_id=run_id,
            )

        # Separar documentos
        approved_docs = []
        rejected_docs = []

        for score_obj, doc in zip(scores, documents):
            doc_with_score = {
                **doc,
                "relevance_score": round(score_obj.relevance_score, 4),
            }

            if score_obj.is_approved:
                approved_docs.append(doc_with_score)
            else:
                rejected_docs.append(doc_with_score)

        # Orderar por score
        approved_docs.sort(
            key=lambda x: x["relevance_score"],
            reverse=True,
        )
        rejected_docs.sort(
            key=lambda x: x["relevance_score"],
            reverse=True,
        )

        approval_rate = len(approved_docs) / len(documents) if documents else 0.0

        logger.info(
            "documents_filtered",
            total=len(documents),
            approved=len(approved_docs),
            rejected=len(rejected_docs),
            approval_rate=round(approval_rate, 4),
            run_id=run_id,
        )

        return FilteredDocumentsResult(
            approved_documents=approved_docs,
            rejected_documents=rejected_docs,
            scores=scores,
            threshold_applied=threshold,
            total_documents=len(documents),
            approved_count=len(approved_docs),
            rejected_count=len(rejected_docs),
            approval_rate=approval_rate,
            run_id=run_id,
        )

    def batch_filter_documents(
        self,
        theme: str,
        document_batches: list[list[dict[str, Any]]],
        threshold: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> list[FilteredDocumentsResult]:
        """
        Filtra múltiplos lotes de documentos.

        Útil para processar resultados de múltiplas APIs.

        Args:
            theme: Tema/query.
            document_batches: Lista de lotes de documentos.
            threshold: Threshold customizado.
            run_id: ID da requisição.

        Returns:
            Lista de FilteredDocumentsResult, um por lote.
        """
        results = []

        for batch in document_batches:
            result = self.filter_documents(
                theme=theme,
                documents=batch,
                threshold=threshold,
                run_id=run_id,
            )
            results.append(result)

        logger.info(
            "batch_documents_filtered",
            batches_count=len(document_batches),
            run_id=run_id,
        )

        return results
