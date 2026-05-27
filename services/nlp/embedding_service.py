"""
Embedding generation service using sentence-transformers.
"""

from typing import Optional, Union

import numpy as np

from core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Serviço de geração de embeddings para textos.

    Usa sentence-transformers para gerar representações semânticas
    de textos, permitindo comparação de similaridade.
    """

    # Modelo padrão (leve e rápido)
    _DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        """
        Inicializa o serviço de embeddings.

        Args:
            model_name: Nome do modelo sentence-transformer.
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """
        Inicializa modelo sentence-transformer.

        Carrega o modelo ou registra aviso se não disponível.
        """
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
            logger.info("embedding_model_initialized", model=self.model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed")
            self.model = None
        except Exception as exc:
            logger.error(f"Failed to initialize embedding model: {exc}")
            self.model = None

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Gera embedding para um texto.

        Args:
            text: Texto para embedding.

        Returns:
            Array numpy com embedding (384 dimensões para all-MiniLM-L6-v2).
            None se modelo não estiver disponível.
        """
        if not text or not text.strip():
            return None

        if not self.model:
            logger.warning("Embedding model not available")
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)

            logger.debug(
                "text_embedded",
                text_length=len(text),
                embedding_shape=embedding.shape,
            )

            return embedding

        except Exception as exc:
            logger.error(f"Failed to embed text: {exc}")
            return None

    def embed_batch(
        self,
        texts: list[str],
        show_progress_bar: bool = False,
    ) -> list[Optional[np.ndarray]]:
        """
        Gera embeddings para múltiplos textos em batch.

        Args:
            texts: Lista de textos.
            show_progress_bar: Se True, mostra barra de progresso.

        Returns:
            Lista de arrays numpy com embeddings.
        """
        if not texts or not self.model:
            return [None] * len(texts)

        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=show_progress_bar,
            )

            logger.info(
                "batch_embedded",
                texts_count=len(texts),
                embedding_shape=embeddings.shape,
            )

            return [emb for emb in embeddings]

        except Exception as exc:
            logger.error(f"Failed to embed batch: {exc}")
            return [None] * len(texts)

    def embed_document(
        self,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        full_text: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """
        Gera embedding para um documento.

        Estratégia de fallback:
        1. Usar abstract se disponível e não vazio
        2. Senão, usar title + abstract
        3. Senão, usar title
        4. Senão, usar full_text

        Args:
            title: Título do documento.
            abstract: Resumo do documento.
            full_text: Texto completo do documento.

        Returns:
            Array numpy com embedding.
            None se nenhum texto disponível.
        """
        # Estratégia 1: Abstract se robusto o suficiente
        if abstract and len(abstract.strip()) > 50:
            embedding = self.embed_text(abstract)
            if embedding is not None:                return embedding

        # Estratégia 2: Título + Abstract
        if title and abstract:
            combined = f"{title}. {abstract}"
            embedding = self.embed_text(combined)
            if embedding is not None:                return embedding

        # Estratégia 3: Apenas título
        if title:
            embedding = self.embed_text(title)
            if embedding is not None:                return embedding

        # Estratégia 4: Texto completo
        if full_text:
            # Truncar para primeiros 512 tokens aproximadamente
            truncated = " ".join(full_text.split()[:200])
            embedding = self.embed_text(truncated)
            if embedding is not None:                return embedding

        logger.warning("No text available for embedding")
        return None

    def embed_documents_batch(
        self,
        documents: list[dict],
    ) -> list[Optional[np.ndarray]]:
        """
        Gera embeddings para múltiplos documentos em batch.

        Args:
            documents: Lista de dicts com 'title', 'abstract', 'full_text'.

        Returns:
            Lista de arrays numpy com embeddings.
        """
        embeddings = []

        for doc in documents:
            embedding = self.embed_document(
                title=doc.get("title"),
                abstract=doc.get("abstract"),
                full_text=doc.get("full_text"),
            )
            embeddings.append(embedding)

        logger.info("documents_batch_embedded", documents_count=len(documents))

        return embeddings

    def get_embedding_dimension(self) -> Optional[int]:
        """
        Retorna dimensionalidade dos embeddings.

        Returns:
            Número de dimensões ou None se modelo não inicializado.
        """
        if not self.model:
            return None

        try:
            # Gerar embedding de teste para descobrir dimensionalidade
            test_embedding = self.embed_text("test")
            return len(test_embedding) if test_embedding is not None else None
        except Exception as exc:
            logger.error(f"Failed to get embedding dimension: {exc}")
            return None
