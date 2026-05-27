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

    def __init__(self, keybert_model: Optional[Any] = None, doc_type: str = "patent"):
        """
        Initialize term extractor.

        Args:
            keybert_model: Pre-loaded KeyBERT model. If None, will load default.
            doc_type: Document type ('patent' or 'scholarly'). Controls which stopwords to use.
        """
        self.keybert = keybert_model
        self.doc_type = doc_type
        self.nlp = None

        # Load config with stopwords and penalties
        self._load_stopwords_config()

        # Load spaCy model
        self._load_spacy_model()

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

    def _load_pos_patterns_config(self) -> None:
        """Load POS patterns (bad bigrams/trigrams) from config."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "pos_patterns.json"
            with open(config_path, "r", encoding="utf-8") as f:
                pos_config = json.load(f)

            # Convert to tuples for matching
            self.bad_pos_bigrams = [tuple(pattern) for pattern in pos_config.get("pos_patterns", {}).get("bad_bigrams", [])]
            self.bad_pos_trigrams = [tuple(pattern) for pattern in pos_config.get("pos_patterns", {}).get("bad_trigrams", [])]

            logger.info(
                "pos_patterns_config_loaded",
                bad_bigrams=len(self.bad_pos_bigrams),
                bad_trigrams=len(self.bad_pos_trigrams),
            )
        except Exception as e:
            logger.warning(
                "pos_patterns_config_load_failed",
                error=str(e),
            )
            self.bad_pos_bigrams = []
            self.bad_pos_trigrams = []

    def _load_stopwords_config(self) -> None:
        """Load stopwords and filtering rules from config/extract-terms.json."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "extract-terms.json"
            with open(config_path, "r", encoding="utf-8") as f:
                self.full_config = json.load(f)

            # Get rules and scoring
            self.rules = self.full_config.get("rules", {})
            self.scoring = self.full_config.get("scoring", {})

            # Get document-type specific config
            doc_config = self.full_config.get(self.doc_type, {})
            common_config = self.full_config.get("common", {})

            # Hard tokens that remove entire term if present
            self.hard_token_remove = set(doc_config.get("hard_token_remove", []))

            # Bad n-gram endings to filter (end of n-gram)
            self.bad_ngram_endings = set(
                doc_config.get("bad_ngram_endings", []) +
                common_config.get("bad_ngram_endings", [])
            )

            # Bad n-gram starts to filter (beginning of n-gram)
            self.bad_ngram_starts = set(
                doc_config.get("bad_ngram_starts", []) +
                common_config.get("bad_ngram_starts", [])
            )

            # Tokens to remove BEFORE n-gram generation
            self.remove_before_ngrams = set(doc_config.get("remove_before_ngrams", []))

            # Phrases to remove entirely
            self.remove_phrases = set(doc_config.get("remove_phrases", []))

            # Generic unigrams that get penalized (but may appear in multiword terms)
            self.generic_unigrams_penalty = set(
                doc_config.get("generic_unigrams_penalty", []) +
                common_config.get("generic_unigrams_penalty", [])
            )

            # Generic unigrams to remove entirely
            self.generic_unigrams_remove = set(
                doc_config.get("generic_unigrams_remove", []) +
                common_config.get("generic_unigrams_remove", [])
            )

            # Generic verbs that get penalized
            self.generic_verbs_penalty = set(
                doc_config.get("generic_verbs_penalty", [])
            )

            # Generic adjectives that get penalized (scholarly only)
            self.generic_adjectives_penalty = set(
                doc_config.get("generic_adjectives_penalty", [])
            )

            # Top 10000 English stopwords (optional expansion)
            if self.rules.get("use_top_10000_english_stopwords", False):
                self.top_10000_stopwords = set(
                    common_config.get("top_10000_english_stopwords_remove", [])
                )
            else:
                self.top_10000_stopwords = set()

            logger.info(
                "extract_terms_config_loaded",
                doc_type=self.doc_type,
                hard_tokens=len(self.hard_token_remove),
                bad_endings=len(self.bad_ngram_endings),
                bad_starts=len(self.bad_ngram_starts),
                remove_before=len(self.remove_before_ngrams),
                penalty_unigrams=len(self.generic_unigrams_penalty),
                penalty_verbs=len(self.generic_verbs_penalty),
                penalty_adjectives=len(self.generic_adjectives_penalty),
                top_10000_enabled=self.rules.get("use_top_10000_english_stopwords", False),
            )
        except Exception as e:
            logger.warning(
                "extract_terms_config_load_failed",
                error=str(e),
            )
            self._init_default_config()

    def _init_default_config(self) -> None:
        """Initialize with minimal default config."""
        self.full_config = {}
        self.rules = {}
        self.scoring = {}
        self.hard_token_remove = set()
        self.bad_ngram_endings = set()
        self.bad_ngram_starts = set()
        self.remove_before_ngrams = set()
        self.remove_phrases = set()
        self.generic_unigrams_penalty = set()
        self.generic_unigrams_remove = set()
        self.generic_verbs_penalty = set()
        self.generic_adjectives_penalty = set()
        self.top_10000_stopwords = set()

    def _clean_text(self, text: str) -> str:
        """
        Clean text: lowercase, remove punctuation, extra spaces, and noise phrases.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text)

        # Remove remove_phrases (boilerplate text)
        for phrase in self.remove_phrases:
            text = text.replace(phrase, ' ')

        # Remove remove_before_ngrams tokens
        for token in self.remove_before_ngrams:
            text = re.sub(r'\b' + re.escape(token) + r'\b', ' ', text)

        # Normalize hyphens to spaces if configured
        if self.rules.get("normalize_hyphen_to_space", True):
            text = text.replace('-', ' ')

        # Strip punctuation if configured
        if self.rules.get("strip_punctuation", True):
            text = re.sub(r'[^\w\s]', ' ', text)

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

        Args:
            chunk_text: Cleaned noun chunk text

        Returns:
            List of cleaned sub-n-grams
        """
        if not self.nlp:
            tokens = chunk_text.split()
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

        for n in range(1, max_n + 1):
            for i in range(len(tokens) - n + 1):
                subngram_tokens = tokens[i : i + n]
                if self.nlp and pos_tags:
                    subngram_pos = pos_tags[i : i + n]
                    subngram_tokens = self._clean_pos_tags(subngram_tokens, subngram_pos)

                if subngram_tokens and len(" ".join(subngram_tokens)) > 2:
                    ngrams.append(" ".join(subngram_tokens))

        return ngrams

    def _tokenize_ngrams(self, text: str, n_range: tuple = (1, 3)) -> list[str]:
        """
        Extract n-grams from text with strict filtering based on config rules.

        Filters based on:
        - hard_token_remove: removes entire term if token present
        - bad_ngram_endings: removes if ends with bad word
        - generic_unigrams_remove: removes single generic words
        - min token length and ngram structure

        Args:
            text: Cleaned text
            n_range: (min_n, max_n) for n-grams

        Returns:
            List of n-grams
        """
        tokens = text.split()
        ngrams = []
        max_ngram_size = self.rules.get("max_ngram_size", 3)
        min_token_length = self.rules.get("min_token_length", 2)

        for n in range(n_range[0], min(n_range[1] + 1, max_ngram_size + 1)):
            for i in range(len(tokens) - n + 1):
                ngram_tokens = tokens[i:i + n]
                ngram = ' '.join(ngram_tokens)

                # 1. Check minimum token length
                if not all(len(t) >= min_token_length for t in ngram_tokens):
                    continue

                # 2. Remove term if contains hard_token (config rule)
                if self.rules.get("remove_term_if_contains_hard_token", True):
                    if any(t in self.hard_token_remove for t in ngram_tokens):
                        continue

                # 3. Remove term if starts with bad start
                if self.rules.get("remove_term_if_starts_with_bad_start", True):
                    if ngram_tokens[0] in self.bad_ngram_starts:
                        continue

                # 4. Remove term if contains bad ending anywhere
                if self.rules.get("remove_term_if_ends_with_bad_ending", True):
                    # For n-grams: no bad endings allowed at all
                    if any(t in self.bad_ngram_endings for t in ngram_tokens):
                        continue

                # 5. Remove single generic unigrams (config rule)
                if self.rules.get("remove_term_if_single_token_in_generic_unigrams_remove", True):
                    if len(ngram_tokens) == 1 and ngram_tokens[0] in self.generic_unigrams_remove:
                        continue

                # 6. For multi-word terms: preserve even if contains generic words (config rule)
                if not self.rules.get("preserve_multiword_terms_with_generic_words", True):
                    if len(ngram_tokens) > 1:
                        if any(t in self.generic_unigrams_penalty for t in ngram_tokens):
                            continue

                ngrams.append(ngram)

        return ngrams

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

            # If we got few results, try without candidates (KeyBERT's own extraction)
            if len(scores) < len(ngrams) * 0.3:  # Less than 30% coverage
                all_keywords = self.keybert.extract_keywords(
                    combined_text,
                    top_n=min(len(ngrams), 50),
                )

                # Score ngrams based on semantic similarity to KeyBERT keywords
                for ngram in ngrams:
                    if ngram not in scores:
                        ngram_words = set(ngram.lower().split())

                        # Check if ngram partially matches any KeyBERT keyword
                        for keyword, score in all_keywords:
                            keyword_words = set(keyword.lower().split())
                            # Calculate word overlap
                            overlap = len(ngram_words & keyword_words) / max(len(ngram_words), 1)
                            if overlap > 0.5:  # 50%+ word overlap
                                # Scale score by overlap ratio
                                scores[ngram] = max(scores.get(ngram, 0), float(score) * overlap)

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

        Args:
            texts: List of texts to analyze
            ngrams: List of candidate terms

        Returns:
            Dict mapping term -> tfidf_score (0-1)
        """
        scores = {}

        try:
            vectorizer = TfidfVectorizer(analyzer='word', lowercase=True)
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = set(vectorizer.get_feature_names_out())

            # Calculate scores for each ngram
            for ngram in ngrams:
                ngram_tokens = ngram.split()

                # If ngram is in vocabulary, use direct score
                if ngram in feature_names:
                    idx = list(vectorizer.get_feature_names_out()).index(ngram)
                    scores[ngram] = float(tfidf_matrix[:, idx].mean())
                else:
                    # For multi-word ngrams, average the component tokens
                    if len(ngram_tokens) > 1:
                        component_scores = []
                        for token in ngram_tokens:
                            if token in feature_names:
                                idx = list(vectorizer.get_feature_names_out()).index(token)
                                component_scores.append(float(tfidf_matrix[:, idx].mean()))

                        if component_scores:
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
        if self.nlp:
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

        # Apply generic unigram penalty (only for single words)
        if len(tokens) == 1:
            if ngram in self.generic_unigrams_penalty:
                penalty += self.scoring.get("generic_unigram_penalty", -0.3)
            if ngram in self.generic_verbs_penalty:
                penalty += self.scoring.get("generic_verb_penalty", -0.4)
            if ngram in self.generic_adjectives_penalty:
                penalty += self.scoring.get("generic_adjective_penalty", -0.25)

        # Apply hard token penalty
        if any(t in self.hard_token_remove for t in tokens):
            penalty += self.scoring.get("hard_token_penalty", -1.0)

        # Apply bad ending penalty
        if tokens[-1] in self.bad_ngram_endings:
            penalty += self.scoring.get("bad_ending_penalty", -1.0)

        return bonus, penalty

    def extract_and_rank_terms(
        self,
        original_params: dict[str, Any],
        enriched_results: list[dict[str, Any]],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Extract and rank relevant terms from enriched results.

        Process:
        1. Extract title and abstract separately from each result
        2. Clean and tokenize into n-grams with source tracking
        3. Score with KeyBERT (semantic) and TF-IDF (statistical)
        4. Apply configurable weights: title (default 3.0) vs abstract (default 1.0)
        5. Combine scores
        6. Remove original terms and generic terms
        7. Rank by combined weighted score

        Args:
            original_params: Original search parameters
            enriched_results: Results with enriched biblio data
            top_k: Number of top terms to return

        Returns:
            List of terms with scores, ordered by relevance
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
            if self.nlp:
                # Extract noun chunks and convert to sub-n-grams
                chunks = self._extract_noun_chunks(text)
                ngrams = []
                for chunk in chunks:
                    ngrams.extend(self._extract_subngramas_from_chunk(chunk))
            else:
                # Fallback to regex-based if spaCy unavailable
                ngrams = self._tokenize_ngrams(text)

            all_ngrams.extend(ngrams)
            ngram_frequency.update(ngrams)
            for ngram in ngrams:
                if ngram not in ngram_sources:
                    ngram_sources[ngram] = {"title": 0, "abstract": 0}
                ngram_sources[ngram]["title"] += 1

        # Process abstracts with spaCy noun_chunks
        for text in abstract_texts:
            if self.nlp:
                # Extract noun chunks and convert to sub-n-grams
                chunks = self._extract_noun_chunks(text)
                ngrams = []
                for chunk in chunks:
                    ngrams.extend(self._extract_subngramas_from_chunk(chunk))
            else:
                # Fallback to regex-based if spaCy unavailable
                ngrams = self._tokenize_ngrams(text)

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

        # Combine scores: 60% KeyBERT, 40% TF-IDF, weighted by source (title vs abstract)
        w_keybert = 0.6
        w_tfidf = 0.4

        combined_scores = {}
        score_adjustments = {}  # Store bonus/penalty for transparency

        for ngram in unique_ngrams:
            # Title contribution (combine KeyBERT and TF-IDF without weight yet)
            title_keybert = keybert_title_scores.get(ngram, 0.0)
            title_tfidf = tfidf_title_scores.get(ngram, 0.0)
            title_combined = w_keybert * title_keybert + w_tfidf * title_tfidf

            # Abstract contribution (combine KeyBERT and TF-IDF without weight yet)
            abstract_keybert = keybert_abstract_scores.get(ngram, 0.0)
            abstract_tfidf = tfidf_abstract_scores.get(ngram, 0.0)
            abstract_combined = w_keybert * abstract_keybert + w_tfidf * abstract_tfidf

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

        # Sort by combined score
        ranked_terms = sorted(
            filtered_ngrams,
            key=lambda x: combined_scores.get(x, 0),
            reverse=True,
        )[:top_k]

        # Build result objects with all scores
        result_terms = []
        for term in ranked_terms:
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
                "score": round(combined_scores.get(term, 0), 3),
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
            filtered_terms=len(filtered_ngrams),
            returned_top_k=len(result_terms),
            title_weight=title_weight,
            abstract_weight=abstract_weight,
        )

        return result_terms
