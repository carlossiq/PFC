"""
Extract and rank relevant terms from enriched search results.

Uses spaCy for linguistically-informed n-gram extraction (noun_chunks).
Combines KeyBERT (semantic relevance) and TF-IDF (statistical importance)
to identify new terms not present in original search parameters.
"""

import json
import re
import string
from typing import Any, Optional
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from core.logging import get_logger

logger = get_logger(__name__)

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spacy_not_installed", message="Install spacy for better n-gram extraction")


class TermExtractor:
    """Extract and rank relevant terms from search results."""

    def __init__(self, keybert_model: Optional[Any] = None):
        """
        Initialize term extractor.

        Requires spaCy (en_core_web_sm) to be installed for linguistic analysis.

        Args:
            keybert_model: Pre-loaded KeyBERT model. If None, will load default.
        """
        self.keybert = keybert_model

        # Initialize boundary configs (will be loaded in _load_spacy_model)
        self.ngram_boundary_tokens = set()
        self.bad_pos_bigrams = []
        self.bad_pos_trigrams = []
        self.ngram_boundary_pos = set()

        # Initialize quality filter configs
        self.boundary_stopwords = set()
        self.patent_structural_words = set()
        self.scholarly_structural_words = set()

        # Load spaCy model (required)
        self._load_spacy_model()

        # Load n-gram boundary tokens
        self._load_ngram_boundary_tokens()

        # Load quality filters
        self._load_quality_filter_config()

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

    def _load_spacy_model(self) -> None:
        """Load spaCy model for linguistic analysis."""
        if not SPACY_AVAILABLE:
            logger.warning("spacy_not_available", message="spaCy not installed")
            return

        try:
            # Try to load English model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spacy_model_loaded", model="en_core_web_sm")
        except OSError:
            logger.warning(
                "spacy_model_not_found",
                message="Download with: python -m spacy download en_core_web_sm",
            )
            self.nlp = None

        # Load POS patterns config
        self._load_pos_patterns_config()

    def _load_ngram_boundary_tokens(self) -> None:
        """Load n-gram boundary tokens that split n-grams when encountered."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "ngram_boundary_tokens.json"
            with open(config_path, "r", encoding="utf-8") as f:
                boundary_config = json.load(f)

            self.ngram_boundary_tokens = set(
                token.lower() for token in boundary_config.get("ngram_boundary_tokens", [])
            )

            logger.info(
                "ngram_boundary_tokens_loaded",
                boundary_tokens=len(self.ngram_boundary_tokens),
            )
        except Exception as e:
            logger.warning(
                "ngram_boundary_tokens_load_failed",
                error=str(e),
            )
            self.ngram_boundary_tokens = set()

    def _load_pos_patterns_config(self) -> None:
        """Load POS patterns (bad bigrams/trigrams) and boundary POS tags from config."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "pos_patterns.json"
            with open(config_path, "r", encoding="utf-8") as f:
                pos_config = json.load(f)

            # Convert to tuples for matching
            self.bad_pos_bigrams = [tuple(pattern) for pattern in pos_config.get("pos_patterns", {}).get("bad_bigrams", [])]
            self.bad_pos_trigrams = [tuple(pattern) for pattern in pos_config.get("pos_patterns", {}).get("bad_trigrams", [])]

            # Load boundary POS tags that split n-grams
            self.ngram_boundary_pos = set(pos_config.get("pos_patterns", {}).get("ngram_boundary_pos", []))

            logger.info(
                "pos_patterns_config_loaded",
                bad_bigrams=len(self.bad_pos_bigrams),
                bad_trigrams=len(self.bad_pos_trigrams),
                boundary_pos=len(self.ngram_boundary_pos),
            )
        except Exception as e:
            logger.warning(
                "pos_patterns_config_load_failed",
                error=str(e),
            )
            self.bad_pos_bigrams = []
            self.bad_pos_trigrams = []
            self.ngram_boundary_pos = set()

    def _load_quality_filter_config(self) -> None:
        """Load string quality filter rules (boundary stopwords, structural words)."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "string_quality_filter.json"
            with open(config_path, "r", encoding="utf-8") as f:
                quality_config = json.load(f)

            # Load filter word sets
            filters = quality_config.get("string_quality_filters", {})
            self.boundary_stopwords = set(w.lower() for w in filters.get("boundary_stopwords", {}).get("words", []))
            self.patent_structural_words = set(w.lower() for w in filters.get("patent_structural_words", {}).get("words", []))
            self.scholarly_structural_words = set(w.lower() for w in filters.get("scholarly_structural_words", {}).get("words", []))

            logger.info(
                "quality_filter_config_loaded",
                boundary_stopwords=len(self.boundary_stopwords),
                patent_words=len(self.patent_structural_words),
                scholarly_words=len(self.scholarly_structural_words),
            )
        except Exception as e:
            logger.warning(
                "quality_filter_config_load_failed",
                error=str(e),
            )
            self.boundary_stopwords = set()
            self.patent_structural_words = set()
            self.scholarly_structural_words = set()

    def _clean_text(self, text: str) -> str:
        """
        Clean text: lowercase, remove URLs, normalize hyphens, extra spaces.

        NOTE: Punctuation is NOT removed here - it's kept for spaCy to detect
        boundary tokens (PUNCT POS tags). The n-gram boundary detector will
        split n-grams at punctuation marks.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)

        # Normalize hyphens to spaces
        text = text.replace('-', ' ')

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _clean_pos_tags(self, tokens: list[str], pos_tags: list[str]) -> list[str]:
        """
        Remove unwanted POS tags from beginning and end of token sequence.

        Removes: DET, ADP, CCONJ, SCONJ, PART, PUNCT, SPACE

        Args:
            tokens: List of tokens
            pos_tags: List of POS tags (same length as tokens)

        Returns:
            Cleaned tokens (may be empty list)
        """
        if not tokens:
            return []

        unwanted_pos = {"DET", "ADP", "CCONJ", "SCONJ", "PART", "PUNCT", "SPACE", "SYM"}

        # Find first good token
        start_idx = 0
        for i, pos in enumerate(pos_tags):
            if pos not in unwanted_pos:
                start_idx = i
                break
        else:
            return []  # All tokens are unwanted

        # Find last good token
        end_idx = len(tokens) - 1
        for i in range(len(pos_tags) - 1, -1, -1):
            if pos_tags[i] not in unwanted_pos:
                end_idx = i
                break

        return tokens[start_idx : end_idx + 1]

    def _extract_noun_chunks(self, text: str) -> list[str]:
        """
        Extract noun chunks from text using spaCy.

        Returns cleaned chunks (with unwanted POS tags removed from start/end).

        Args:
            text: Text to analyze

        Returns:
            List of cleaned noun chunks
        """
        if not self.nlp:
            return []

        try:
            doc = self.nlp(text)
            chunks = []

            for chunk in doc.noun_chunks:
                # Get tokens and POS tags
                tokens = [token.text.lower() for token in chunk]
                pos_tags = [token.pos_ for token in chunk]

                # Clean POS tags from start/end
                cleaned = self._clean_pos_tags(tokens, pos_tags)

                if cleaned and len(" ".join(cleaned)) > 2:  # Min length check
                    chunks.append(" ".join(cleaned))

            return chunks
        except Exception as e:
            logger.warning(
                "noun_chunk_extraction_failed",
                error=str(e),
            )
            return []

    def _extract_subngramas_from_chunk(self, chunk_text: str) -> list[str]:
        """
        Extract sub-n-grams (n=1-3) from a noun chunk with POS cleaning.

        Does not generate n-grams that:
        - Traverse boundary tokens (defined in ngram_boundary_tokens)
        - Contain boundary POS tags (ADP, CCONJ, SCONJ, PUNCT, SPACE)
        - Cross punctuation marks at start/end

        Args:
            chunk_text: Cleaned noun chunk text

        Returns:
            List of cleaned sub-n-grams
        """
        if not self.nlp:
            tokens = chunk_text.split()
            pos_tags = ["NOUN"] * len(tokens)
        else:
            try:
                doc = self.nlp(chunk_text)
                tokens = [token.text.lower() for token in doc]
                pos_tags = [token.pos_ for token in doc]
            except Exception:
                tokens = chunk_text.split()
                pos_tags = ["NOUN"] * len(tokens)

        ngrams = []
        max_n = min(3, len(tokens))

        # Find segments that don't cross boundary tokens/pos
        segments = self._split_by_boundaries(tokens, pos_tags)

        # Extract n-grams from each segment
        for segment_tokens, segment_pos in segments:
            segment_n = min(3, len(segment_tokens))

            for n in range(1, segment_n + 1):
                for i in range(len(segment_tokens) - n + 1):
                    subngram_tokens = segment_tokens[i : i + n]
                    subngram_pos = segment_pos[i : i + n]

                    # Clean POS tags from edges
                    cleaned_tokens = self._clean_pos_tags(subngram_tokens, subngram_pos)

                    if cleaned_tokens and len(" ".join(cleaned_tokens)) > 2:
                        ngrams.append(" ".join(cleaned_tokens))

        return ngrams

    def _split_by_boundaries(self, tokens: list[str], pos_tags: list[str]) -> list[tuple[list[str], list[str]]]:
        """
        Split token sequence by boundary tokens and POS tags.

        Returns list of (tokens, pos_tags) tuples for non-boundary segments.
        Filters out punctuation tokens within segments.

        Args:
            tokens: List of tokens
            pos_tags: List of POS tags

        Returns:
            List of (segment_tokens, segment_pos) tuples
        """
        segments = []
        current_segment = []
        current_pos = []

        for token, pos in zip(tokens, pos_tags):
            # Check if this is a boundary token or POS tag
            is_boundary = (
                token in self.ngram_boundary_tokens
                or pos in self.ngram_boundary_pos
            )

            if is_boundary:
                # End current segment if not empty
                if current_segment:
                    segments.append((current_segment, current_pos))
                    current_segment = []
                    current_pos = []
            else:
                # Add to current segment (skip pure punctuation tokens)
                # Keep token if it contains alphanumeric chars (allow "don't" but not "-")
                if any(c.isalnum() for c in token):
                    current_segment.append(token)
                    current_pos.append(pos)

        # Add final segment
        if current_segment:
            segments.append((current_segment, current_pos))

        return segments if segments else [(tokens, pos_tags)]

    def _extract_keybert_scores(self, texts: list[str], ngrams: list[str]) -> dict[str, float]:
        """
        Extract KeyBERT semantic relevance scores.

        First tries with candidates filter for exact matches, then falls back to
        extracting all keywords if few results are found.

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

            if not combined_text.strip():
                return scores

            # Try with candidates first
            keywords = self.keybert.extract_keywords(
                combined_text,
                candidates=ngrams,
                top_n=min(len(ngrams), 50),
            )

            # Build score dict
            for keyword, score in keywords:
                scores[keyword] = float(score)

            # If we got few results, use fallback: score unmatched ngrams based on word overlap
            # with full keyword extraction
            if len(scores) < len(ngrams) * 0.5:  # Less than 50% coverage
                all_keywords = self.keybert.extract_keywords(
                    combined_text,
                    top_n=min(len(ngrams), 100),
                )

                # Score unmatched ngrams based on word overlap with KeyBERT keywords
                for ngram in ngrams:
                    if ngram not in scores:
                        ngram_words = set(ngram.lower().split())
                        best_score = 0.0

                        # Find best matching keyword and use word overlap to score ngram
                        for keyword, keyword_score in all_keywords:
                            keyword_words = set(keyword.lower().split())
                            # Check if any words overlap
                            common_words = ngram_words & keyword_words
                            if common_words:
                                # Score based on proportion of ngram covered by keyword matches
                                overlap = len(common_words) / len(ngram_words)
                                scaled_score = float(keyword_score) * overlap
                                best_score = max(best_score, scaled_score)

                        if best_score > 0:
                            scores[ngram] = best_score

        except Exception as e:
            logger.warning(
                "keybert_extraction_failed",
                error=str(e),
            )

        return scores

    def _extract_tfidf_scores(self, texts: list[str], ngrams: list[str]) -> dict[str, float]:
        """
        Extract TF-IDF statistical importance scores.

        For n-grams, if not in vocabulary, compute as average of component words.
        Only returns scores for ngrams that actually appear in the texts.

        Args:
            texts: List of texts to analyze
            ngrams: List of candidate terms

        Returns:
            Dict mapping term -> tfidf_score (0-1). Only includes ngrams found in texts.
        """
        scores = {}

        if not texts:
            return scores

        try:
            vectorizer = TfidfVectorizer(analyzer='word', lowercase=True)
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = set(vectorizer.get_feature_names_out())

            # Only score ngrams that actually appear in these texts
            for ngram in ngrams:
                ngram_tokens = ngram.split()

                # If ngram is in vocabulary, use direct score
                if ngram in feature_names:
                    idx = list(vectorizer.get_feature_names_out()).index(ngram)
                    scores[ngram] = float(tfidf_matrix[:, idx].mean())
                else:
                    # For multi-word ngrams, only score if ALL tokens appear
                    # (don't average partial matches across sources)
                    if len(ngram_tokens) > 1 and all(token in feature_names for token in ngram_tokens):
                        component_scores = []
                        for token in ngram_tokens:
                            idx = list(vectorizer.get_feature_names_out()).index(token)
                            component_scores.append(float(tfidf_matrix[:, idx].mean()))
                        scores[ngram] = sum(component_scores) / len(component_scores)

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

    def _get_score_adjustments(self, ngram: str) -> tuple[float, float]:
        """
        Calculate score adjustments (bonus and penalty) for an n-gram.

        Returns: (bonus, penalty) where final_score = base_score + bonus + penalty

        Size-based penalties:
        - 1-gram: -0.4
        - 2-gram: 0.0
        - 3-gram: +0.3

        POS pattern penalties:
        - Bad bigram/trigram patterns: -0.8

        Args:
            ngram: The n-gram to check

        Returns:
            Tuple of (bonus_adjustment, penalty_adjustment)
        """
        tokens = ngram.split()
        bonus = 0.0
        penalty = 0.0

        # Apply n-gram size-based penalties
        n_words = len(tokens)
        if n_words == 1:
            penalty += -0.4  # Unigram penalty
        elif n_words == 2:
            bonus += 0.0  # Bigram: no adjustment
        elif n_words == 3:
            bonus += 0.3  # Trigram bonus

        # Apply POS pattern penalties using spaCy
        try:
            doc = self.nlp(ngram)
            pos_tags = tuple(token.pos_ for token in doc)

            # Check against bad bigram patterns
            if n_words == 2 and pos_tags in self.bad_pos_bigrams:
                penalty += -0.8
            # Check against bad trigram patterns
            elif n_words == 3 and pos_tags in self.bad_pos_trigrams:
                penalty += -0.8

        except Exception as e:
            logger.warning(
                "pos_pattern_check_failed",
                error=str(e),
                ngram=ngram,
            )

        return bonus, penalty

    def _apply_subsumption_filter(
        self,
        ranked_terms: list[str],
    ) -> list[str]:
        """
        Apply subsumption filter: remove terms that are subsets of other terms.

        If "ultrafiltration membrane" appears after "composite ultrafiltration membrane",
        remove the shorter one since it's subsumed by the longer, more specific term.

        Args:
            ranked_terms: List of terms already sorted by score (descending)

        Returns:
            List of terms with subsumed terms removed, preserving order and scores
        """
        kept_terms = []
        kept_terms_set = set()

        for term in ranked_terms:
            term_words = set(term.lower().split())
            is_subsumed = False

            # Check if this term is subsumed by any already kept term
            for kept_term in kept_terms:
                kept_words = set(kept_term.lower().split())
                # If all words of this term are in a kept term, it's subsumed
                if term_words.issubset(kept_words) and term_words != kept_words:
                    is_subsumed = True
                    logger.debug(
                        "term_subsumed",
                        subsumed_term=term,
                        by_term=kept_term,
                    )
                    break

            if not is_subsumed:
                kept_terms.append(term)
                kept_terms_set.add(term)

        return kept_terms

    def _apply_quality_filters(self, candidate_terms: list[str]) -> list[str]:
        """
        Apply string quality filters to remove low-quality terms.

        Removes terms that:
        1. Start or end with boundary stopwords (a, an, the, of, etc.)
        2. Contain patent structural words (wherein, comprising, said, etc.)
        3. Contain scholarly structural words (proposed, analyzed, novel, etc.)

        Args:
            candidate_terms: List of terms to filter

        Returns:
            List of terms that pass quality checks
        """
        filtered_terms = []

        for term in candidate_terms:
            term_lower = term.lower()
            words = term_lower.split()

            # Check boundary stopwords (start or end)
            if words and (words[0] in self.boundary_stopwords or words[-1] in self.boundary_stopwords):
                continue

            # Check patent structural words (anywhere in term)
            if any(word in self.patent_structural_words for word in words):
                continue

            # Check scholarly structural words (anywhere in term)
            if any(word in self.scholarly_structural_words for word in words):
                continue

            # Term passes all quality filters
            filtered_terms.append(term)

        return filtered_terms

    def _calculate_mmr_ranking(
        self,
        candidates: list[str],
        scores: dict[str, float],
        lambda_param: float = 0.4,
        top_k: int = 20,
        similarity_threshold: float = 0.5,
    ) -> list[str]:
        """
        Rank terms using Maximal Marginal Relevance (MMR) with hard diversity constraint.

        MMR = lambda * relevance_score - (1 - lambda) * max_similarity_to_selected

        Hard constraint: Skip terms with >similarity_threshold overlap with selected terms.

        With lambda=0.4 and threshold=0.5:
        - 40% weight on relevance (high-scoring terms)
        - 60% weight on diversity (avoiding similar terms)
        - Skip any term >50% similar to already selected terms

        Args:
            candidates: List of candidate terms to rank
            scores: Dict mapping term -> relevance_score
            lambda_param: Weight for relevance vs diversity (0-1), default 0.4
            top_k: Number of top terms to return
            similarity_threshold: Skip terms more similar than this (0-1)

        Returns:
            List of top-k terms ranked by MMR with diversity guarantee
        """
        if not candidates or top_k <= 0:
            return []

        # Use Jaccard similarity for word overlap diversity
        def jaccard_similarity(term_a: str, term_b: str) -> float:
            words_a = set(term_a.lower().split())
            words_b = set(term_b.lower().split())
            if not words_a or not words_b:
                return 0.0
            intersection = len(words_a & words_b)
            union = len(words_a | words_b)
            return intersection / union if union > 0 else 0.0

        selected = []
        remaining = set(candidates)

        # Iteratively select top-k terms by MMR with hard similarity constraint
        for _ in range(min(top_k, len(candidates))):
            best_term = None
            best_mmr = float("-inf")

            for candidate in remaining:
                relevance = scores.get(candidate, 0.0)

                # Calculate diversity penalty: max similarity to any already selected term
                if selected:
                    max_similarity = max(jaccard_similarity(candidate, term) for term in selected)

                    # Hard constraint: Skip if too similar to any selected term
                    if max_similarity > similarity_threshold:
                        continue
                else:
                    max_similarity = 0.0

                # MMR score = lambda * relevance - (1 - lambda) * diversity_penalty
                mmr = lambda_param * relevance - (1 - lambda_param) * max_similarity

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_term = candidate

            # Add best term to selected and remove from remaining
            if best_term is not None:
                selected.append(best_term)
                remaining.remove(best_term)
            else:
                break

        return selected

    def extract_and_rank_terms(
        self,
        original_params: dict[str, Any],
        enriched_results: list[dict[str, Any]],
        top_k: int = None,  # Deprecated: all terms above score threshold are returned
    ) -> list[dict[str, Any]]:
        """
        Extract and rank relevant terms from enriched results.

        Process:
        1. Extract title and abstract separately from each result
        2. Clean and tokenize into n-grams with source tracking
        3. Score with KeyBERT (semantic) and TF-IDF (statistical)
        4. Normalize scores separately: KeyBERT and TF-IDF to 0-1 scale
        5. Combine scores: 60% TF-IDF + 40% KeyBERT, weighted by source
        6. Apply configurable weights: title (default 3.0) vs abstract (default 1.0)
        7. Apply quality filters (stopwords, structural words)
        8. Apply MMR ranking (relevance + diversity)
        9. Apply subsumption filter (remove subset terms)
        10. Apply score threshold filter (keep only scores >= threshold)

        Args:
            original_params: Original search parameters
            enriched_results: Results with enriched biblio data
            top_k: Deprecated, ignored. All terms above score threshold are returned.

        Returns:
            List of terms with scores, ordered by relevance (filtered by score threshold)
        """
        from core.config import settings

        # Normalize original parameters
        original_terms = self._normalize_original_params(original_params)

        # Extract title and abstract weights from config
        title_weight = getattr(settings, "term_extraction_title_weight", 3.0)
        abstract_weight = getattr(settings, "term_extraction_abstract_weight", 1.0)

        # Extract texts from results (separated by source)
        title_texts = []
        abstract_texts = []
        text_to_result = {}

        for idx, result in enumerate(enriched_results):
            # Try to extract from biblio structure first, then fallback to direct access
            biblio = result.get("biblio", {})

            if biblio:
                title = (biblio.get("invention_title", "") or biblio.get("title", "")).strip()
                abstract = (biblio.get("abstract", "") or "").strip()
            else:
                # Direct access if no biblio key (newer data structure)
                title = (result.get("invention_title", "") or result.get("title", "")).strip()
                abstract = (result.get("abstract", "") or "").strip()

            # Skip if both title and abstract are empty
            if not title and not abstract:
                continue

            # Process title separately (if non-empty)
            if title:
                cleaned_title = self._clean_text(title)
                title_texts.append(cleaned_title)
                text_to_result[cleaned_title] = {
                    "source": "title",
                    "publication_number": result.get("publication_number") or result.get("family_id"),
                }

            # Process abstract separately (if non-empty)
            if abstract:
                cleaned_abstract = self._clean_text(abstract)
                abstract_texts.append(cleaned_abstract)
                text_to_result[cleaned_abstract] = {
                    "source": "abstract",
                    "publication_number": result.get("publication_number") or result.get("family_id"),
                }

        # Combine all texts for unified n-gram extraction
        all_texts = title_texts + abstract_texts
        if not all_texts:
            return []

        # Extract n-grams using spaCy noun_chunks (linguistically-informed)
        all_ngrams = []
        ngram_frequency = Counter()
        ngram_sources = {}  # Track which sources each ngram comes from

        # Process titles with spaCy noun_chunks
        for text in title_texts:
            # Extract noun chunks and convert to sub-n-grams
            chunks = self._extract_noun_chunks(text)
            ngrams = []
            for chunk in chunks:
                ngrams.extend(self._extract_subngramas_from_chunk(chunk))

            all_ngrams.extend(ngrams)
            ngram_frequency.update(ngrams)
            for ngram in ngrams:
                if ngram not in ngram_sources:
                    ngram_sources[ngram] = {"title": 0, "abstract": 0}
                ngram_sources[ngram]["title"] += 1

        # Process abstracts with spaCy noun_chunks
        for text in abstract_texts:
            # Extract noun chunks and convert to sub-n-grams
            chunks = self._extract_noun_chunks(text)
            ngrams = []
            for chunk in chunks:
                ngrams.extend(self._extract_subngramas_from_chunk(chunk))

            all_ngrams.extend(ngrams)
            ngram_frequency.update(ngrams)
            for ngram in ngrams:
                if ngram not in ngram_sources:
                    ngram_sources[ngram] = {"title": 0, "abstract": 0}
                ngram_sources[ngram]["abstract"] += 1

        # Remove duplicates
        unique_ngrams = list(dict.fromkeys(all_ngrams))  # Preserve order, remove dupes

        if not unique_ngrams:
            return []

        logger.info(
            "term_extraction_ngrams_extracted",
            total_ngrams=len(unique_ngrams),
            title_documents=len(title_texts),
            abstract_documents=len(abstract_texts),
        )

        # Extract KeyBERT scores separately for title and abstract
        keybert_title_scores = self._extract_keybert_scores(title_texts, unique_ngrams) if title_texts else {}
        keybert_abstract_scores = self._extract_keybert_scores(abstract_texts, unique_ngrams) if abstract_texts else {}

        # Extract TF-IDF scores separately for title and abstract
        tfidf_title_scores = self._extract_tfidf_scores(title_texts, unique_ngrams) if title_texts else {}
        tfidf_abstract_scores = self._extract_tfidf_scores(abstract_texts, unique_ngrams) if abstract_texts else {}

        # Normalize scores separately (0-1 scale) to avoid scale mismatch
        # TF-IDF scores are already normalized in _extract_tfidf_scores
        # KeyBERT scores need normalization to match TF-IDF scale
        def normalize_scores(scores_dict: dict[str, float]) -> dict[str, float]:
            """Normalize scores to 0-1 range."""
            if not scores_dict:
                return {}
            max_score = max(scores_dict.values()) if scores_dict else 1.0
            if max_score == 0:
                return scores_dict
            return {term: score / max_score for term, score in scores_dict.items()}

        # Normalize KeyBERT scores separately for title and abstract
        keybert_title_scores = normalize_scores(keybert_title_scores)
        keybert_abstract_scores = normalize_scores(keybert_abstract_scores)

        # Combine scores: 60% TF-IDF + 40% KeyBERT, weighted by source (title vs abstract)
        w_tfidf = 0.6
        w_keybert = 0.4

        combined_scores = {}
        score_adjustments = {}  # Store bonus/penalty for transparency

        for ngram in unique_ngrams:
            # Title contribution (combine normalized TF-IDF and KeyBERT)
            title_keybert = keybert_title_scores.get(ngram, 0.0)
            title_tfidf = tfidf_title_scores.get(ngram, 0.0)
            title_combined = w_tfidf * title_tfidf + w_keybert * title_keybert

            # Abstract contribution (combine normalized TF-IDF and KeyBERT)
            abstract_keybert = keybert_abstract_scores.get(ngram, 0.0)
            abstract_tfidf = tfidf_abstract_scores.get(ngram, 0.0)
            abstract_combined = w_tfidf * abstract_tfidf + w_keybert * abstract_keybert

            # Final score: apply weights during weighted average calculation
            if title_combined > 0 and abstract_combined > 0:
                # Present in both sources: weighted average
                base_score = (title_combined * title_weight + abstract_combined * abstract_weight) / (
                    title_weight + abstract_weight
                )
            elif title_combined > 0:
                # Only in title
                base_score = title_combined
            elif abstract_combined > 0:
                # Only in abstract
                base_score = abstract_combined
            else:
                # Not found in either
                base_score = 0.0

            # Apply score adjustments based on config rules
            bonus, penalty = self._get_score_adjustments(ngram)
            final_score = base_score + bonus + penalty
            final_score = max(0, final_score)  # Don't allow negative scores

            combined_scores[ngram] = final_score
            score_adjustments[ngram] = (bonus, penalty)

        # Filter out original terms: remove only unigrams that match original_params
        # Keep n-grams (2+ words) even if they contain original terms
        filtered_ngrams = [
            ng for ng in unique_ngrams
            if ng not in original_terms  # Remove exact matches
            and not (len(ng.split()) == 1 and any(ot in ng.split() for ot in original_terms))  # Remove unigrams only
        ]

        logger.info(
            "term_extraction_filtered",
            original_terms_removed=len(unique_ngrams) - len(filtered_ngrams),
        )

        # Apply string quality filters (remove boilerplate/structural words)
        filtered_ngrams = self._apply_quality_filters(filtered_ngrams)

        logger.info(
            "term_extraction_quality_filtered",
            remaining_terms=len(filtered_ngrams),
        )

        # Load configuration for MMR and filtering
        score_threshold = getattr(settings, "term_extraction_score_threshold", 0.6)
        mmr_lambda = getattr(settings, "term_extraction_mmr_lambda", 0.4)
        mmr_similarity_threshold = getattr(settings, "term_extraction_mmr_similarity_threshold", 0.5)

        # Rank by MMR (Maximal Marginal Relevance)
        # Returns all candidates ordered by relevance + diversity (no top_k limit)
        ranked_terms = self._calculate_mmr_ranking(
            candidates=filtered_ngrams,
            scores=combined_scores,
            lambda_param=mmr_lambda,
            top_k=len(filtered_ngrams),  # Return all, will filter by score later
            similarity_threshold=mmr_similarity_threshold,
        )

        logger.info(
            "term_extraction_mmr_ranked",
            mmr_lambda=mmr_lambda,
            mmr_threshold=mmr_similarity_threshold,
            candidates_ranked=len(ranked_terms),
        )

        # Apply subsumption filter: remove terms that are subsets of other terms
        ranked_terms = self._apply_subsumption_filter(ranked_terms)

        logger.info(
            "term_extraction_subsumption_filtered",
            terms_after_subsumption=len(ranked_terms),
        )

        # Build result objects with all scores, filtering by score threshold
        result_terms = []
        terms_below_threshold = 0

        for term in ranked_terms:
            term_score = combined_scores.get(term, 0)

            # Filter by score threshold
            if term_score < score_threshold:
                terms_below_threshold += 1
                logger.debug(
                    "term_below_score_threshold",
                    term=term,
                    score=term_score,
                    threshold=score_threshold,
                )
                continue

            sources = ngram_sources.get(term, {})
            source_list = []
            if sources.get("title", 0) > 0:
                source_list.append("title")
            if sources.get("abstract", 0) > 0:
                source_list.append("abstract")

            bonus, penalty = score_adjustments.get(term, (0.0, 0.0))
            n_words = len(term.split())

            result_terms.append({
                "term": term,
                "score": round(term_score, 3),
                "n_words": n_words,
                "keybert_score_title": round(keybert_title_scores.get(term, 0), 3) if title_texts else None,
                "keybert_score_abstract": round(keybert_abstract_scores.get(term, 0), 3) if abstract_texts else None,
                "tf_idf_score_title": round(tfidf_title_scores.get(term, 0), 3) if title_texts else None,
                "tf_idf_score_abstract": round(tfidf_abstract_scores.get(term, 0), 3) if abstract_texts else None,
                "frequency": ngram_frequency.get(term, 0),
                "sources": source_list,
                "score_bonus": round(bonus, 3),
                "score_penalty": round(penalty, 3),
                "title_weight": title_weight,
                "abstract_weight": abstract_weight,
            })

        logger.info(
            "term_extraction_complete",
            total_unique_terms=len(unique_ngrams),
            after_quality_filter=len(filtered_ngrams),
            after_subsumption=len(ranked_terms),
            below_score_threshold=terms_below_threshold,
            returned_count=len(result_terms),
            score_threshold=score_threshold,
            title_weight=title_weight,
            abstract_weight=abstract_weight,
        )

        return result_terms
