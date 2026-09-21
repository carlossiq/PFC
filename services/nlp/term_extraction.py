"""
Extract and rank relevant terms from enriched search results.

Uses spaCy + KeyphraseVectorizers (PatternRank: adjective*+noun+ grammar
pattern) for candidate generation, BM25F for lexical/statistical scoring,
KeyBERT for semantic scoring, and Reciprocal Rank Fusion (RRF, 2 stages) to
combine channels and rank candidates. C-value replaces the old word-overlap
subsumption filter for nested-term redundancy.

Ver TESTE_EXTRACAO_TERMOS_BM25F_RRF.md para a comparação com o pipeline
anterior (spaCy noun_chunks + TF-IDF + KeyBERT combinados linearmente).
"""

import json
import math
import re
from typing import Any, Optional
from collections import Counter
from pathlib import Path

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning(
        "spacy_not_installed", message="Install spacy for candidate generation"
    )

try:
    from keyphrase_vectorizers import KeyphraseCountVectorizer

    KEYPHRASE_VECTORIZERS_AVAILABLE = True
except ImportError:
    KEYPHRASE_VECTORIZERS_AVAILABLE = False
    logger.warning(
        "keyphrase_vectorizers_not_installed",
        message="Install keyphrase-vectorizers for candidate generation",
    )


class TermExtractor:
    """Extract and rank relevant terms from search results."""

    # Padrão gramatical do PatternRank: adjetivo(s) opcional(is) seguido de
    # substantivo(s) - casa a frase nominal MAXIMAL, não janelas deslizantes.
    _KEYPHRASE_POS_PATTERN = "<J.*>*<N.*>+"
    # Teto de tamanho do candidato. KeyphraseCountVectorizer não tem parâmetro
    # de tamanho máximo (verificado: sua assinatura não aceita max_words) -
    # o corte é feito depois, sobre os candidatos já extraídos. 5 em vez do
    # antigo teto rígido de 3: o pipeline anterior cortava modificadores
    # importantes de frases nominais de 4+ palavras (ver relatório de teste,
    # ex. "graphene oxide modified membrane" virava "oxide modified
    # membrane"); 5 é uma folga generosa sem permitir frases patológicas.
    _MAX_CANDIDATE_WORDS = 5

    def __init__(self, keybert_model: Optional[Any] = None):
        """
        Initialize term extractor.

        Requires spaCy (en_core_web_sm) e keyphrase-vectorizers para geração
        de candidatos, e KeyBERT para o canal semântico.

        Args:
            keybert_model: Pre-loaded KeyBERT model. If None, will load default.
        """
        self.keybert = keybert_model

        # Initialize POS pattern configs (loaded in _load_spacy_model)
        self.bad_pos_bigrams = []
        self.bad_pos_trigrams = []
        self.ngram_boundary_pos = set()

        # Initialize quality filter configs
        self.boundary_stopwords = set()
        self.patent_structural_words = set()
        self.scholarly_structural_words = set()

        # Load spaCy model + keyphrase vectorizer (required)
        self._load_spacy_model()

        # Load quality filters
        self._load_quality_filter_config()

        if not self.keybert:
            try:
                from keybert import KeyBERT

                # Load model name from config (default: generic multilingual)
                model_name = getattr(
                    settings,
                    "llm_keybert_model",
                    "distiluse-base-multilingual-cased-v2",
                )
                self.keybert = KeyBERT(model=model_name)
                logger.info(
                    "keybert_model_loaded",
                    model=model_name,
                )
            except Exception as e:
                logger.warning(
                    "keybert_initialization_failed",
                    error=str(e),
                )
                self.keybert = None

    def _load_spacy_model(self) -> None:
        """Load spaCy model + PatternRank keyphrase vectorizer."""
        if not SPACY_AVAILABLE:
            logger.warning("spacy_not_available", message="spaCy not installed")
            self.nlp = None
            self.keyphrase_vectorizer = None
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

        # Load POS patterns config (bad bigram/trigram patterns)
        self._load_pos_patterns_config()

        if self.nlp and KEYPHRASE_VECTORIZERS_AVAILABLE:
            # Reusa o pipeline spaCy já carregado (mesmo custo de carga caro
            # de antes) em vez de deixar o KeyphraseCountVectorizer carregar
            # o seu próprio.
            self.keyphrase_vectorizer = KeyphraseCountVectorizer(
                spacy_pipeline=self.nlp,
                pos_pattern=self._KEYPHRASE_POS_PATTERN,
                stop_words=None,  # filtro de stopwords já feito em _apply_quality_filters
                lowercase=True,
            )
        else:
            self.keyphrase_vectorizer = None
            if not KEYPHRASE_VECTORIZERS_AVAILABLE:
                logger.warning(
                    "keyphrase_vectorizers_not_available",
                    message="keyphrase-vectorizers not installed",
                )

    def _load_pos_patterns_config(self) -> None:
        """Load POS patterns (bad bigrams/trigrams) from config."""
        try:
            config_path = (
                Path(__file__).parent.parent.parent / "config" / "pos_patterns.json"
            )
            with open(config_path, "r", encoding="utf-8") as f:
                pos_config = json.load(f)

            # Convert to tuples for matching
            self.bad_pos_bigrams = [
                tuple(pattern)
                for pattern in pos_config.get("pos_patterns", {}).get("bad_bigrams", [])
            ]
            self.bad_pos_trigrams = [
                tuple(pattern)
                for pattern in pos_config.get("pos_patterns", {}).get(
                    "bad_trigrams", []
                )
            ]

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

    def _load_quality_filter_config(self) -> None:
        """Load string quality filter rules (boundary stopwords, structural words)."""
        try:
            config_path = (
                Path(__file__).parent.parent.parent
                / "config"
                / "string_quality_filter.json"
            )
            with open(config_path, "r", encoding="utf-8") as f:
                quality_config = json.load(f)

            # Load filter word sets
            filters = quality_config.get("string_quality_filters", {})
            self.boundary_stopwords = set(
                w.lower()
                for w in filters.get("boundary_stopwords", {}).get("words", [])
            )
            self.patent_structural_words = set(
                w.lower()
                for w in filters.get("patent_structural_words", {}).get("words", [])
            )
            self.scholarly_structural_words = set(
                w.lower()
                for w in filters.get("scholarly_structural_words", {}).get("words", [])
            )

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

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r"http\S+|www.\S+", "", text)

        # Normalize hyphens to spaces
        text = text.replace("-", " ")

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _extract_candidates_patternrank(self, texts: list[str]) -> list[str]:
        """
        Generate term candidates via PatternRank (KeyphraseCountVectorizer):
        matches the adjective*+noun+ grammar pattern across the whole text,
        returning the MAXIMAL noun phrase (not 1-3 word sliding windows like
        the previous spaCy noun_chunks pipeline).

        Args:
            texts: List of cleaned texts to analyze

        Returns:
            List of unique candidate terms, order-preserved
        """
        if not self.keyphrase_vectorizer or not texts:
            return []

        # KeyphraseCountVectorizer não detecta a fronteira entre um texto da
        # lista e o próximo quando o texto não termina em pontuação de fim de
        # frase (títulos, por exemplo, quase nunca têm ponto final). Sem essa
        # fronteira, o padrão gramatical "vaza" de um texto pro seguinte e
        # produz candidatos que não existem em NENHUM dos dois textos
        # originais (ex.: "seawater desalination process membrane filtration
        # device", concatenando o fim de um título com o início do próximo) -
        # e reduz drasticamente a quantidade de candidatos extraídos
        # (confirmado empiricamente: 5 títulos sem ponto final -> 5
        # candidatos, vários deles cruzados; com ponto final -> 10
        # candidatos, todos corretos). Garantir pontuação final por texto
        # antes do fit() resolve isso.
        #
        # Mesmo problema DENTRO de um texto: vírgula/ponto-e-vírgula não são
        # tratados como fronteira de frase pelo vetorizador (só reconhece
        # .!?), então itens de uma lista separados por vírgula colam num
        # candidato que não existe no texto original (ex.: "filtration,
        # purification of water" -> candidato espúrio "filtration
        # purification"). Convertendo pra ponto força a fronteira.
        bounded_texts = [
            text.replace(",", ".").replace(";", ".")
            for text in texts
        ]
        bounded_texts = [
            text if text.rstrip().endswith((".", "!", "?")) else f"{text}."
            for text in bounded_texts
        ]

        try:
            self.keyphrase_vectorizer.fit(bounded_texts)
            candidates = list(self.keyphrase_vectorizer.get_feature_names_out())
        except ValueError:
            # KeyphraseCountVectorizer raises ValueError when no candidate is
            # found in the text (equivalent to the old unique_ngrams == [])
            return []
        except Exception as e:
            logger.warning("patternrank_extraction_failed", error=str(e))
            return []

        return [
            candidate
            for candidate in candidates
            if 1 <= len(candidate.split()) <= self._MAX_CANDIDATE_WORDS
        ]

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

    def _matches_bad_pos_pattern(self, term: str) -> bool:
        """
        Check whether a bi/trigram's POS tag sequence matches a known "bad"
        grammatical pattern (config/pos_patterns.json), e.g. ADV+VERB
        ("efficiently removes") - a strong signal the phrase is a verb-like
        fragment rather than a genuine noun-phrase term.

        Only applies to exactly 2 or 3-word terms (the only lengths with
        configured patterns).
        """
        n_words = len(term.split())
        if n_words not in (2, 3) or not self.nlp:
            return False

        try:
            doc = self.nlp(term)
            pos_tags = tuple(token.pos_ for token in doc)
        except Exception as e:
            logger.warning("pos_pattern_check_failed", error=str(e), ngram=term)
            return False

        if n_words == 2:
            return pos_tags in self.bad_pos_bigrams
        return pos_tags in self.bad_pos_trigrams

    def _structural_quality_score(self, term: str) -> float:
        """
        Structural quality signal for a candidate: n-gram size preference
        (same weights as the old additive bonus/penalty) plus a penalty for
        bad POS patterns. Used only to RANK candidates against each other via
        RRF (§ extract_and_rank_terms) - not summed into any other score.
        """
        tokens = term.split()
        n_words = len(tokens)

        unigram_penalty = getattr(settings, "term_extraction_unigram_penalty", -0.4)
        bigram_bonus = getattr(settings, "term_extraction_bigram_bonus", 0.0)
        trigram_bonus = getattr(settings, "term_extraction_trigram_bonus", 0.25)

        size_score = {1: unigram_penalty, 2: bigram_bonus}.get(n_words, trigram_bonus)

        if self._matches_bad_pos_pattern(term):
            bad_bigram_penalty = getattr(
                settings, "term_extraction_bad_bigram_penalty", -0.8
            )
            bad_trigram_penalty = getattr(
                settings, "term_extraction_bad_trigram_penalty", -0.8
            )
            size_score += bad_bigram_penalty if n_words == 2 else bad_trigram_penalty

        return size_score

    @staticmethod
    def _rrf_fuse_two_rankings(
        candidates: list[str],
        score_a: dict[str, float],
        score_b: dict[str, float],
        k: int,
    ) -> dict[str, float]:
        """
        Reciprocal Rank Fusion of two scored channels: RRF(t) = sum(1/(k+rank_i(t))).
        Used both for BM25F x KeyBERT (-> salience_score) and salience x
        structural quality (-> final_rrf_score).
        """
        rank_a = {
            term: i + 1
            for i, term in enumerate(
                sorted(candidates, key=lambda t: score_a.get(t, 0.0), reverse=True)
            )
        }
        rank_b = {
            term: i + 1
            for i, term in enumerate(
                sorted(candidates, key=lambda t: score_b.get(t, 0.0), reverse=True)
            )
        }
        return {
            term: 1.0 / (k + rank_a[term]) + 1.0 / (k + rank_b[term])
            for term in candidates
        }

    def _compute_bm25f_scores(
        self,
        candidates: list[str],
        documents: list[dict[str, str]],
        title_weight: float,
        abstract_weight: float,
    ) -> dict[str, float]:
        """
        BM25F (field-weighted BM25) lexical score per candidate against the
        in-memory corpus, replacing sklearn TfidfVectorizer's column-mean.
        Each candidate is treated as a phrase; term frequency is the literal
        substring occurrence count per field (equivalent to Lucene phrase
        frequency without needing an inverted index for this small,
        per-request corpus).

        Args:
            candidates: Candidate terms
            documents: Per-document {"title": str, "abstract": str} pairs
            title_weight / abstract_weight: Field weights (same settings used
                before for the linear title/abstract combination)

        Returns:
            Dict mapping term -> aggregate BM25F score across the corpus
        """
        n_docs = len(documents)
        if n_docs == 0 or not candidates:
            return {}

        k1 = getattr(settings, "term_extraction_bm25_k1", 1.2)
        b = getattr(settings, "term_extraction_bm25_b", 0.75)

        title_lens = [len(doc["title"].split()) for doc in documents]
        abstract_lens = [len(doc["abstract"].split()) for doc in documents]
        avg_title_len = (sum(title_lens) / n_docs) or 1.0
        avg_abstract_len = (sum(abstract_lens) / n_docs) or 1.0

        scores: dict[str, float] = {}

        for term in candidates:
            doc_pseudo_tfs = []

            for doc, title_len, abstract_len in zip(documents, title_lens, abstract_lens):
                tf_title = doc["title"].count(term)
                tf_abstract = doc["abstract"].count(term)
                if tf_title == 0 and tf_abstract == 0:
                    continue

                b_title = (1 - b) + b * (title_len / avg_title_len)
                b_abstract = (1 - b) + b * (abstract_len / avg_abstract_len)
                pseudo_tf = title_weight * (tf_title / b_title) + abstract_weight * (
                    tf_abstract / b_abstract
                )
                doc_pseudo_tfs.append(pseudo_tf)

            n_t = len(doc_pseudo_tfs)
            if n_t == 0:
                continue

            idf = math.log(1 + (n_docs - n_t + 0.5) / (n_t + 0.5))
            scores[term] = sum(tf / (k1 + tf) * idf for tf in doc_pseudo_tfs)

        return scores

    def _extract_keybert_scores(
        self, texts: list[str], ngrams: list[str]
    ) -> dict[str, float]:
        """
        Extract KeyBERT semantic relevance scores (cosine similarity channel).

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

    @staticmethod
    def _is_contiguous_substring(shorter_words: list[str], longer_words: list[str]) -> bool:
        """Check if shorter is a contiguous word-subsequence of longer."""
        return " ".join(shorter_words) in " ".join(longer_words)

    def _compute_c_values(
        self, candidates: list[str], frequency: dict[str, int]
    ) -> dict[str, float]:
        """
        Classic C-value (Frantzi & Ananiadou). Replaces the old word-overlap
        subsumption filter (overlap_ratio >= 0.66). A candidate that only ever
        occurs embedded inside longer candidates (no independent frequency)
        gets a low/negative c_value and is dropped downstream.

        Note: since PatternRank (unlike the old sliding-window generator)
        already emits maximal noun phrases instead of every sub-window, far
        fewer candidates are pure fragments of another to begin with - this
        mostly catches near-duplicate phrasing across different documents
        (e.g. "wireless charging" nested inside "electric vehicle wireless
        charging pads").

        Args:
            candidates: Candidate terms
            frequency: term -> raw occurrence count (ngram_frequency)

        Returns:
            Dict mapping term -> c_value
        """
        nested_in: dict[str, list[str]] = {term: [] for term in candidates}
        by_length_desc = sorted(candidates, key=lambda t: len(t.split()), reverse=True)

        for longer in by_length_desc:
            longer_words = longer.split()
            for shorter in candidates:
                if shorter == longer:
                    continue
                shorter_words = shorter.split()
                if len(shorter_words) >= len(longer_words):
                    continue
                if self._is_contiguous_substring(shorter_words, longer_words):
                    nested_in[shorter].append(longer)

        c_values = {}
        for term in candidates:
            n_words = len(term.split())
            f = frequency.get(term, 0)
            longer_terms = nested_in[term]

            if not longer_terms:
                c_values[term] = math.log2(max(n_words, 2)) * f
            else:
                freq_in_longer = sum(frequency.get(t, 0) for t in longer_terms)
                c_values[term] = math.log2(max(n_words, 2)) * (
                    f - freq_in_longer / len(longer_terms)
                )

        return c_values

    def _deduplicate_nested_terms(self, ranked_terms: list[str]) -> list[str]:
        """
        Drop a term when a term already kept (therefore ranked >= it, since
        ranked_terms is sorted by score descending) contiguously contains it
        as a nested phrase - keeps only the best-scored member of each
        nested family (e.g. "composite ultrafiltration membrane" over
        "ultrafiltration membrane" when the former ranks higher).

        Only catches strict nesting (shorter is a contiguous word-subsequence
        of an already-kept longer term, same definition as C-value's - see
        _is_contiguous_substring); a partial overlap like "composite
        membrane" inside "composite ultrafiltration membrane" (not
        contiguous - "ultrafiltration" sits between them) is not nesting and
        both survive independently.

        Args:
            ranked_terms: Terms already sorted by score, descending.

        Returns:
            Same order, with dominated nested terms removed.
        """
        kept: list[str] = []
        for term in ranked_terms:
            term_words = term.split()
            if any(
                len(term_words) < len(kept_term.split())
                and self._is_contiguous_substring(term_words, kept_term.split())
                for kept_term in kept
            ):
                continue
            kept.append(term)
        return kept

    def _apply_quality_filters(self, candidate_terms: list[str]) -> list[str]:
        """
        Apply string quality filters to clean up low-quality terms.

        1. Trims boundary stopwords (a, an, the, of, etc.) off both ends,
           repeatedly - a stopword can be exposed right after stripping the
           one before it (e.g. "the good permeability" -> "good
           permeability" -> "permeability") - instead of discarding the
           whole candidate for having one at the edge.
        2. Drops the term entirely if, after trimming, it still contains a
           patent structural word (wherein, comprising, said, etc.) anywhere.
        3. Drops the term entirely if, after trimming, it still contains a
           scholarly structural word (proposed, analyzed, novel, etc.)
           anywhere.

        Trimming can collapse two different candidates onto the same string
        (e.g. "good permeability" and "high permeability" both trim to
        "permeability") - deduplicated here, first occurrence wins.

        Args:
            candidate_terms: List of terms to filter

        Returns:
            List of terms (order-preserved, deduplicated) that pass quality
            checks - some trimmed relative to the input.
        """
        filtered_terms = []
        seen = set()

        for term in candidate_terms:
            words = term.split()

            changed = True
            while words and changed:
                changed = False
                if words[0].lower() in self.boundary_stopwords:
                    words = words[1:]
                    changed = True
                if words and words[-1].lower() in self.boundary_stopwords:
                    words = words[:-1]
                    changed = True

            if not words:
                continue

            words_lower = [w.lower() for w in words]

            # Check patent structural words (anywhere in the trimmed term)
            if any(w in self.patent_structural_words for w in words_lower):
                continue

            # Check scholarly structural words (anywhere in the trimmed term)
            if any(w in self.scholarly_structural_words for w in words_lower):
                continue

            trimmed_term = " ".join(words)
            if trimmed_term in seen:
                continue
            seen.add(trimmed_term)
            filtered_terms.append(trimmed_term)

        return filtered_terms

    def extract_and_rank_terms(
        self,
        original_params: dict[str, Any],
        enriched_results: list[dict[str, Any]],
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract and rank relevant terms from enriched results.

        Process:
        1. Extract title/abstract per document (biblio fallback), clean text
        2. Generate candidates via PatternRank (KeyphraseVectorizers,
           adjective*+noun+ grammar pattern) over the combined corpus
        3. Track frequency and title/abstract presence per candidate
        4. Filter out original search terms (unigrams only) and structural
           boilerplate (patent/scholarly word lists)
        5. Score candidates: BM25F (lexical, field-weighted title/abstract)
           and KeyBERT (semantic) against the corpus
        6. Fuse BM25F + KeyBERT ranks via RRF -> salience_score
        7. Score structural quality (n-gram size + bad POS pattern)
        8. Fuse salience + quality ranks via RRF -> final_rrf_score
        9. Compute C-value per candidate (nested-term redundancy signal);
           drop candidates whose c_value collapses to <= 0
        10. Rank by final_rrf_score, apply score threshold, cap at
            MAX_RETURNED_TERMS

        Args:
            original_params: Original search parameters
            enriched_results: Results with enriched biblio data
            score_threshold: Minimum final_rrf_score to keep a term. Defaults
                to settings.term_extraction_score_threshold when omitted.

        Returns:
            List of terms with scores, ordered by relevance (filtered by score threshold)
        """
        from core.config import settings

        # Normalize original parameters
        original_terms = self._normalize_original_params(original_params)

        # Extract title and abstract weights from config (also used as BM25F field weights)
        title_weight = getattr(settings, "term_extraction_title_weight", 3.0)
        abstract_weight = getattr(settings, "term_extraction_abstract_weight", 1.0)

        # Per-document {title, abstract} pairs, needed for field-weighted
        # BM25F (unlike the old flat title_texts/abstract_texts lists, the
        # two fields must stay aligned per document), plus the flat lists
        # PatternRank/KeyBERT expect.
        documents: list[dict[str, str]] = []
        title_texts: list[str] = []
        abstract_texts: list[str] = []

        for result in enriched_results:
            # Try to extract from biblio structure first, then fallback to direct access
            biblio = result.get("biblio", {})

            if biblio:
                title = (
                    biblio.get("invention_title", "") or biblio.get("title", "")
                ).strip()
                abstract = (biblio.get("abstract", "") or "").strip()
            else:
                # Direct access if no biblio key (newer data structure)
                title = (
                    result.get("invention_title", "") or result.get("title", "")
                ).strip()
                abstract = (result.get("abstract", "") or "").strip()

            # Skip if both title and abstract are empty
            if not title and not abstract:
                continue

            title_clean = self._clean_text(title) if title else ""
            abstract_clean = self._clean_text(abstract) if abstract else ""

            documents.append({"title": title_clean, "abstract": abstract_clean})
            if title_clean:
                title_texts.append(title_clean)
            if abstract_clean:
                abstract_texts.append(abstract_clean)

        all_texts = title_texts + abstract_texts
        if not all_texts:
            return []

        # Candidate generation: PatternRank (grammar-pattern maximal noun
        # phrases) over the whole corpus, replacing spaCy noun_chunks + 1-3
        # word sliding-window sub-n-grams.
        unique_ngrams = self._extract_candidates_patternrank(all_texts)

        if not unique_ngrams:
            return []

        logger.info(
            "term_extraction_ngrams_extracted",
            total_ngrams=len(unique_ngrams),
            title_documents=len(title_texts),
            abstract_documents=len(abstract_texts),
        )

        # Filter out original terms: remove only unigrams that match original_params
        # Keep n-grams (2+ words) even if they contain original terms
        filtered_ngrams = [
            ng
            for ng in unique_ngrams
            if ng not in original_terms  # Remove exact matches
            and not (
                len(ng.split()) == 1 and any(ot in ng.split() for ot in original_terms)
            )  # Remove unigrams only
        ]

        logger.info(
            "term_extraction_filtered",
            original_terms_removed=len(unique_ngrams) - len(filtered_ngrams),
        )

        # Apply string quality filters (trims boundary stopwords, drops terms
        # with structural boilerplate anywhere - see _apply_quality_filters).
        # Runs BEFORE frequency/source tracking below because trimming can
        # change the term string (e.g. "good permeability" -> "permeability"),
        # and possibly collapse two different candidates onto the same
        # trimmed string (deduplicated inside _apply_quality_filters) - both
        # cases would desync a frequency dict keyed by the pre-trim string.
        filtered_ngrams = self._apply_quality_filters(filtered_ngrams)

        logger.info(
            "term_extraction_quality_filtered",
            remaining_terms=len(filtered_ngrams),
        )

        if not filtered_ngrams:
            return []

        # Frequency and source tracking (occurrence count via substring scan -
        # candidates are full phrases now, not tokens from an indexed pass)
        ngram_frequency: Counter = Counter()
        ngram_sources: dict[str, dict[str, int]] = {
            term: {"title": 0, "abstract": 0} for term in filtered_ngrams
        }
        for term in filtered_ngrams:
            for text in title_texts:
                count = text.count(term)
                if count:
                    ngram_frequency[term] += count
                    ngram_sources[term]["title"] += 1
            for text in abstract_texts:
                count = text.count(term)
                if count:
                    ngram_frequency[term] += count
                    ngram_sources[term]["abstract"] += 1

        # Lexical channel: BM25F, field-weighted (title/abstract)
        bm25f_scores = self._compute_bm25f_scores(
            filtered_ngrams, documents, title_weight, abstract_weight
        )

        # Semantic channel: KeyBERT cosine similarity against the combined
        # corpus text (same model/method as before - only how it feeds the
        # final score changes, from a linear 0.6/0.4 blend to RRF)
        semantic_scores = (
            self._extract_keybert_scores(all_texts, filtered_ngrams)
            if self.keybert
            else {}
        )

        rrf_k = getattr(settings, "term_extraction_rrf_k", 60)

        # 1st RRF stage: fuse lexical (BM25F) and semantic (KeyBERT) ranks
        salience_scores = self._rrf_fuse_two_rankings(
            filtered_ngrams, bm25f_scores, semantic_scores, k=rrf_k
        )

        # Structural quality: n-gram size preference + bad POS pattern penalty
        quality_scores = {
            term: self._structural_quality_score(term) for term in filtered_ngrams
        }

        # 2nd RRF stage: fuse salience and structural quality ranks -> final score
        final_scores = self._rrf_fuse_two_rankings(
            filtered_ngrams, salience_scores, quality_scores, k=rrf_k
        )

        # C-value: redundancy signal between nested candidate phrases
        # (replaces the word-overlap subsumption filter)
        c_values = self._compute_c_values(filtered_ngrams, ngram_frequency)

        min_frequency = getattr(settings, "term_extraction_cvalue_min_frequency", 1)
        surviving_ngrams = [
            term
            for term in filtered_ngrams
            if ngram_frequency.get(term, 0) >= min_frequency
            and c_values.get(term, 0.0) > 0
        ]

        logger.info(
            "term_extraction_cvalue_filtered",
            terms_after_cvalue=len(surviving_ngrams),
        )

        # Rank by final RRF score (descending)
        ranked_terms = sorted(
            surviving_ngrams, key=lambda t: final_scores.get(t, 0.0), reverse=True
        )

        # Drop a term when a higher-ranked term already kept contiguously
        # contains it (e.g. "ultrafiltration membrane" when "composite
        # ultrafiltration membrane" ranks higher and is already in the
        # list) - keeps only the best-scored member of each nested family,
        # instead of cluttering the checklist with near-duplicate nestings.
        # Runs before the score threshold/cap below so a redundant nested
        # variant doesn't spend threshold/cap budget that a genuinely new
        # term could use.
        ranked_terms = self._deduplicate_nested_terms(ranked_terms)

        # Apply score threshold (recalibrated for the RRF scale - the old
        # 0-1 threshold does not apply, see TESTE_EXTRACAO_TERMOS_BM25F_RRF.md)
        if score_threshold is None:
            score_threshold = settings.term_extraction_score_threshold

        above_threshold = []
        below_threshold = []
        for term in ranked_terms:
            if final_scores.get(term, 0.0) >= score_threshold:
                above_threshold.append(term)
            else:
                below_threshold.append(term)
        terms_filtered_by_score = len(below_threshold)

        # final_rrf_score is RANK-relative within this batch (RRF, not an
        # absolute quality scale) - its numeric range shifts with batch size
        # and candidate-quality composition, so a fixed threshold can leave
        # an entire batch below the cutoff (observed: a 315-candidate batch
        # where even the #1-ranked term scored under 0.024, returning 0
        # terms). Top up with the next best-ranked terms below the
        # threshold rather than leaving the user with an empty checklist -
        # above_threshold/below_threshold are both slices of the same
        # score-sorted ranked_terms, so the concatenation stays sorted.
        min_returned_terms = getattr(settings, "term_extraction_min_returned_terms", 10)
        topped_up = 0
        if len(above_threshold) < min_returned_terms:
            needed = min_returned_terms - len(above_threshold)
            topped_up = min(needed, len(below_threshold))
            ranked_terms = above_threshold + below_threshold[:needed]
        else:
            ranked_terms = above_threshold

        # Teto de termos devolvidos - inalterado (ver EXTRACAO_TERMOS_NGRAMAS.md §14)
        MAX_RETURNED_TERMS = 60
        terms_capped = len(ranked_terms) - min(len(ranked_terms), MAX_RETURNED_TERMS)
        ranked_terms = ranked_terms[:MAX_RETURNED_TERMS]

        logger.info(
            "term_extraction_score_filtered",
            score_threshold=score_threshold,
            filtered_by_score=terms_filtered_by_score,
            topped_up_below_threshold=topped_up,
            terms_capped=terms_capped,
            final_terms=len(ranked_terms),
        )

        # Build result objects with all scores

        # `final_rrf_score` é o score exposto ao frontend, sem normalização -
        # vive sempre num range matemático estreito (~0.018-0.033, soma de
        # dois termos 1/(k+rank), k=60 - ver TESTE_EXTRACAO_TERMOS_BM25F_RRF.md).
        # Já teve uma versão normalizada (min-max 0-1 dentro do lote) só pra
        # exibição, mas foi removida - quem precisar de uma escala 0-1
        # comparável (ex: os thresholds specific/balanced/generic de
        # ChatService._terms_context_suffix) normaliza no próprio ponto de
        # uso, sobre o lote que fizer sentido ali (ver esse método).
        result_terms = []

        for term in ranked_terms:
            sources = ngram_sources.get(term, {})
            source_list = []
            if sources.get("title", 0) > 0:
                source_list.append("title")
            if sources.get("abstract", 0) > 0:
                source_list.append("abstract")

            result_terms.append(
                {
                    "term": term,
                    "salience_score": round(salience_scores.get(term, 0.0), 5),
                    "quality_score": round(quality_scores.get(term, 0.0), 3),
                    "final_rrf_score": round(final_scores.get(term, 0.0), 5),
                    "c_value": round(c_values.get(term, 0.0), 3),
                    "n_words": len(term.split()),
                    "frequency": ngram_frequency.get(term, 0),
                    "sources": source_list,
                }
            )

        logger.info(
            "term_extraction_complete",
            total_unique_terms=len(unique_ngrams),
            after_quality_filter=len(filtered_ngrams),
            after_cvalue=len(surviving_ngrams),
            returned_count=len(result_terms),
            score_threshold=score_threshold,
            title_weight=title_weight,
            abstract_weight=abstract_weight,
        )

        return result_terms


_term_extractor: Optional["TermExtractor"] = None


def get_term_extractor() -> "TermExtractor":
    """
    Devolve uma instância compartilhada de TermExtractor, criada na primeira
    chamada e reaproveitada daí em diante - carregar spaCy e o modelo do
    KeyBERT é caro (leitura de disco + checagem de cache com o huggingface a
    cada carga), e TermExtractor não guarda nenhum estado mutável específico
    de uma extração entre chamadas, então é seguro compartilhar uma única
    instância entre requisições concorrentes.
    """
    global _term_extractor
    if _term_extractor is None:
        _term_extractor = TermExtractor()
    return _term_extractor
