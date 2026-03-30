"""
Keyword extraction service using KeyBERT.
"""

from typing import Optional

from core.logging import get_logger

logger = get_logger(__name__)


class KeywordService:
    """
    Serviço de extração de palavras-chave de documentos.

    Usa KeyBERT para extrair termos principais de textos,
    útil para capturar conceitos centrais de documentos.
    """

    def __init__(self, language: str = "english", top_k: int = 10) -> None:
        """
        Inicializa o serviço de keywords.

        Args:
            language: Idioma para extração (english, portuguese, etc).
            top_k: Número padrão de keywords a extrair.
        """
        self.language = language
        self.top_k = top_k
        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """
        Inicializa modelo KeyBERT.

        Carregando modelo sob demanda para evitar overhead se não usar.
        """
        try:
            from keybert import KeyBERT

            self.model = KeyBERT(model="all-MiniLM-L6-v2")
            logger.info("keybert_model_initialized", language=self.language)
        except ImportError:
            logger.warning("keybert not installed, keyword extraction will be limited")
            self.model = None
        except Exception as exc:
            logger.error(f"Failed to initialize KeyBERT: {exc}")
            self.model = None

    def extract_keywords(
        self,
        text: str,
        top_k: Optional[int] = None,
        min_df: int = 1,
        max_df: float = 0.95,
    ) -> list[tuple[str, float]]:
        """
        Extrai palavras-chave de um texto.

        Args:
            text: Texto para extrair palavras-chave.
            top_k: Número de keywords (usa padrão se None).
            min_df: Frequência mínima do documento.
            max_df: Frequência máxima do documento.

        Returns:
            Lista de tuplas (keyword, score) ordenadas por score descendente.
        """
        if not text or not text.strip():
            return []

        if not self.model:
            logger.warning("KeyBERT model not available, returning empty keywords")
            return []

        top_k = top_k or self.top_k

        try:
            keywords = self.model.extract_keywords(
                text,
                language=self.language,
                top_n=top_k,
                min_df=min_df,
                max_df=max_df,
            )

            logger.debug(
                "keywords_extracted",
                text_length=len(text),
                keywords_count=len(keywords),
            )

            return keywords

        except Exception as exc:
            logger.error(f"Failed to extract keywords: {exc}")
            return []

    def extract_from_document(
        self,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        full_text: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Extrai palavras-chave de múltiplos campos de um documento.

        Processa título, resumo e texto completo separadamente,
        permitindo análise granular por campo.

        Args:
            title: Título do documento.
            abstract: Resumo/abstract do documento.
            full_text: Texto completo do documento.
            top_k: Número de keywords por campo.

        Returns:
            Dicionário com keywords por campo:
            {
                "title": [(keyword, score), ...],
                "abstract": [(keyword, score), ...],
                "full_text": [(keyword, score), ...],
                "combined": [(keyword, score), ...]
            }
        """
        results = {
            "title": [],
            "abstract": [],
            "full_text": [],
            "combined": [],
        }

        # Extrair de cada campo individualmente
        if title:
            results["title"] = self.extract_keywords(title, top_k)

        if abstract:
            results["abstract"] = self.extract_keywords(abstract, top_k)

        if full_text:
            results["full_text"] = self.extract_keywords(full_text, top_k)

        # Extrair de texto combinado (melhor contexto)
        combined_text = " ".join([field for field in [title, abstract, full_text] if field])

        if combined_text:
            combined_keywords = self.extract_keywords(combined_text, top_k)
            # Remover duplicatas mantendo score mais alto
            seen = {kw[0]: kw[1] for kw in combined_keywords}
            results["combined"] = sorted(
                seen.items(),
                key=lambda x: x[1],
                reverse=True,
            )

        logger.debug(
            "document_keywords_extracted",
            title_keywords=len(results["title"]),
            abstract_keywords=len(results["abstract"]),
            combined_keywords=len(results["combined"]),
        )

        return results

    def batch_extract(
        self,
        documents: list[dict[str, Optional[str]]],
        top_k: Optional[int] = None,
    ) -> list[dict[str, list[tuple[str, float]]]]:
        """
        Extrai palavras-chave de múltiplos documentos em batch.

        Args:
            documents: Lista de dicts com campos 'title', 'abstract', 'full_text'.
            top_k: Número de keywords por documento.

        Returns:
            Lista de dicts com keywords extraídas para cada documento.
        """
        results = []

        for doc in documents:
            extracted = self.extract_from_document(
                title=doc.get("title"),
                abstract=doc.get("abstract"),
                full_text=doc.get("full_text"),
                top_k=top_k,
            )
            results.append(extracted)

        logger.info("batch_keywords_extracted", documents_count=len(documents))

        return results

    def get_unique_keywords(
        self,
        keyword_dicts: list[dict[str, list[tuple[str, float]]]],
        deduplicate: bool = True,
    ) -> list[str]:
        """
        Obtém lista única de palavras-chave de múltiplos documentos.

        Útil para construir vocabulário ou listar termos principais.

        Args:
            keyword_dicts: Lista de dicts retornados por batch_extract.
            deduplicate: Se True, remove duplicatas.

        Returns:
            Lista de palavras-chave únicas.
        """
        all_keywords = set() if deduplicate else []

        for doc_keywords in keyword_dicts:
            # Usar "combined" para evitar repetição entre campos
            keywords = doc_keywords.get("combined", [])

            for keyword, _score in keywords:
                if deduplicate:
                    all_keywords.add(keyword)
                else:
                    all_keywords.append(keyword)

        if deduplicate:
            return sorted(list(all_keywords))
        else:
            # Remover duplicatas mantendo ordem
            seen = set()
            result = []
            for kw in all_keywords:
                if kw not in seen:
                    result.append(kw)
                    seen.add(kw)
            return result
