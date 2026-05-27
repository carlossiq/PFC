"""
Extract and rank relevant terms from enriched search results.

Combines KeyBERT (semantic relevance) and TF-IDF (statistical importance)
to identify new terms not present in original search parameters.
"""

import re
import string
from typing import Any, Optional
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from core.logging import get_logger

logger = get_logger(__name__)


class TermExtractor:
    """Extract and rank relevant terms from search results."""

    # Portuguese and English stopwords
    STOPWORDS = {
        # Portuguese
        "o", "a", "os", "as", "um", "uma", "uns", "umas",
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "e", "ou", "mas", "porém", "contudo", "todavia",
        "que", "qual", "quais", "quanto", "quantos", "quando",
        "onde", "por", "para", "com", "sem", "sob", "sobre",
        "este", "esse", "aquele", "isto", "isso", "aquilo",
        "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas",
        "meu", "teu", "seu", "nosso", "vosso",
        "é", "são", "era", "eram", "foi", "foram", "será", "serão",
        "tem", "têm", "tinha", "tinham", "teve", "tiveram",
        "há", "havia", "houve", "haverá",
        # English
        "the", "a", "an", "and", "or", "but", "not", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must",
        "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "that", "this", "these", "those", "which", "who", "what", "where", "when",
        "it", "its", "he", "she", "they", "them", "their",
        "as", "if", "because", "than", "then", "so", "such",
    }

    def __init__(self, keybert_model: Optional[Any] = None):
        """
        Initialize term extractor.

        Args:
            keybert_model: Pre-loaded KeyBERT model. If None, will load default.
        """
        self.keybert = keybert_model
        if not self.keybert:
            try:
                from keybert import KeyBERT
                self.keybert = KeyBERT(model="distiluse-base-multilingual-cased-v2")
            except Exception as e:
                logger.warning(
                    "keybert_initialization_failed",
                    error=str(e),
                )
                self.keybert = None

    def _clean_text(self, text: str) -> str:
        """
        Clean text: lowercase, remove punctuation, extra spaces.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _tokenize_ngrams(self, text: str, n_range: tuple = (1, 3)) -> list[str]:
        """
        Extract n-grams from text (1 to n_range[1] words).

        Args:
            text: Cleaned text
            n_range: (min_n, max_n) for n-grams

        Returns:
            List of n-grams
        """
        tokens = text.split()
        ngrams = []

        for n in range(n_range[0], n_range[1] + 1):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i + n])
                ngram_tokens = ngram.split()

                # Filter criteria
                # 1. Not entirely stopwords
                if all(t in self.STOPWORDS for t in ngram_tokens):
                    continue

                # 2. All tokens > 2 chars
                if not all(len(t) > 2 for t in ngram_tokens):
                    continue

                # 3. At least one non-stopword token
                has_content = any(t not in self.STOPWORDS for t in ngram_tokens)
                if not has_content:
                    continue

                # 4. Remove ngrams with only very short tokens (< 3 chars)
                content_tokens = [t for t in ngram_tokens if t not in self.STOPWORDS]
                if content_tokens and all(len(t) < 3 for t in content_tokens):
                    continue

                ngrams.append(ngram)

        return ngrams

    def _extract_keybert_scores(self, texts: list[str], ngrams: list[str]) -> dict[str, float]:
        """
        Extract KeyBERT semantic relevance scores.

        Args:
            texts: List of texts to analyze
            ngrams: List of candidate terms

        Returns:
            Dict mapping term -> keybert_score (0-1)
        """
        scores = {}

        if not self.keybert or not ngrams:
            return scores

        try:
            # Combine all texts for context
            combined_text = " ".join(texts)

            # Extract keywords with KeyBERT
            keywords = self.keybert.extract_keywords(
                combined_text,
                candidates=ngrams,
                top_n=len(ngrams),
            )

            # Build score dict
            for keyword, score in keywords:
                scores[keyword] = float(score)

        except Exception as e:
            logger.warning(
                "keybert_extraction_failed",
                error=str(e),
            )

        return scores

    def _extract_tfidf_scores(self, texts: list[str], ngrams: list[str]) -> dict[str, float]:
        """
        Extract TF-IDF statistical importance scores.

        Args:
            texts: List of texts to analyze
            ngrams: List of candidate terms

        Returns:
            Dict mapping term -> tfidf_score (0-1)
        """
        scores = {}

        try:
            # Use word-level analyzer to match the n-gram extraction
            vectorizer = TfidfVectorizer(analyzer='word', lowercase=True)

            # Fit on texts
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()

            # Calculate scores for ngrams - check if each ngram is in the vocab
            for ngram in ngrams:
                if ngram in feature_names:
                    idx = list(feature_names).index(ngram)
                    # Average TF-IDF score across all documents
                    scores[ngram] = float(tfidf_matrix[:, idx].mean())

            # Normalize to 0-1
            if scores:
                max_score = max(scores.values())
                if max_score > 0:
                    scores = {k: v / max_score for k, v in scores.items()}

        except Exception as e:
            logger.warning(
                "tfidf_extraction_failed",
                error=str(e),
            )

        return scores

    def _normalize_original_params(self, original_params: dict) -> set[str]:
        """
        Extract and normalize original search parameters.

        Args:
            original_params: Original search parameters (theme, description, etc.)

        Returns:
            Set of normalized terms from original params
        """
        original_terms = set()

        for key, value in original_params.items():
            if isinstance(value, str):
                cleaned = self._clean_text(value)
                original_terms.update(cleaned.split())
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, str):
                        cleaned = self._clean_text(item)
                        original_terms.update(cleaned.split())

        return original_terms

    def extract_and_rank_terms(
        self,
        original_params: dict[str, Any],
        enriched_results: list[dict[str, Any]],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Extract and rank relevant terms from enriched results.

        Process:
        1. Combine title + abstract from each result
        2. Clean and tokenize into n-grams
        3. Score with KeyBERT (semantic) and TF-IDF (statistical)
        4. Combine scores
        5. Remove original terms and generic terms
        6. Rank by combined score

        Args:
            original_params: Original search parameters
            enriched_results: Results with enriched biblio data
            top_k: Number of top terms to return

        Returns:
            List of terms with scores, ordered by relevance
        """
        # Normalize original parameters
        original_terms = self._normalize_original_params(original_params)

        # Extract texts from results
        texts = []
        text_to_result = {}  # Track which result each text comes from

        for idx, result in enumerate(enriched_results):
            biblio = result.get("biblio", {})

            if not biblio:
                continue

            title = biblio.get("title", "")
            abstract = biblio.get("abstract", "")

            if not title and not abstract:
                continue

            combined_text = f"{title} {abstract}"
            cleaned = self._clean_text(combined_text)

            texts.append(cleaned)
            text_to_result[cleaned] = {
                "publication_number": result.get("publication_number"),
                "has_title": bool(title),
                "has_abstract": bool(abstract),
            }

        if not texts:
            return []

        # Extract n-grams from all texts
        all_ngrams = []
        ngram_frequency = Counter()
        ngram_sources = {}

        for text in texts:
            ngrams = self._tokenize_ngrams(text)
            all_ngrams.extend(ngrams)
            ngram_frequency.update(ngrams)

            for ngram in ngrams:
                if ngram not in ngram_sources:
                    ngram_sources[ngram] = {"title": 0, "abstract": 0, "count": 0}
                ngram_sources[ngram]["count"] += 1

        unique_ngrams = list(set(all_ngrams))

        if not unique_ngrams:
            return []

        logger.info(
            "term_extraction_ngrams_extracted",
            total_ngrams=len(unique_ngrams),
            total_documents=len(texts),
        )

        # Extract KeyBERT scores
        keybert_scores = self._extract_keybert_scores(texts, unique_ngrams)

        # Extract TF-IDF scores
        tfidf_scores = self._extract_tfidf_scores(texts, unique_ngrams)

        # Combine scores: 60% KeyBERT, 40% TF-IDF
        w_keybert = 0.6
        w_tfidf = 0.4

        combined_scores = {}
        for ngram in unique_ngrams:
            keybert = keybert_scores.get(ngram, 0.0)
            tfidf = tfidf_scores.get(ngram, 0.0)

            combined = w_keybert * keybert + w_tfidf * tfidf
            combined_scores[ngram] = combined

        # Filter out original terms
        filtered_ngrams = [
            ng for ng in unique_ngrams
            if ng not in original_terms and not any(
                ot in ng.split() for ot in original_terms
            )
        ]

        logger.info(
            "term_extraction_filtered",
            original_terms_removed=len(unique_ngrams) - len(filtered_ngrams),
        )

        # Sort by combined score
        ranked_terms = sorted(
            filtered_ngrams,
            key=lambda x: combined_scores.get(x, 0),
            reverse=True,
        )[:top_k]

        # Build result objects with all scores
        result_terms = []
        for term in ranked_terms:
            result_terms.append({
                "term": term,
                "score": round(combined_scores.get(term, 0), 3),
                "keybert_score": round(keybert_scores.get(term, 0), 3),
                "tf_idf_score": round(tfidf_scores.get(term, 0), 3),
                "frequency": ngram_frequency.get(term, 0),
                "sources": [
                    "title" if "title" in text_to_result.get(t, {}) else "abstract"
                    for t in texts
                ],
            })

        logger.info(
            "term_extraction_complete",
            total_unique_terms=len(unique_ngrams),
            filtered_terms=len(filtered_ngrams),
            returned_top_k=len(result_terms),
        )

        return result_terms
