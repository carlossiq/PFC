# Term Extraction Implementation - Complete

## Summary
Implemented a full term extraction pipeline that combines semantic (KeyBERT) and statistical (TF-IDF) relevance scoring for enriched patent search results.

## Components Implemented

### 1. TermExtractor Class (`services/nlp/term_extraction.py`)
- **N-gram extraction**: 1-3 word phrases with intelligent filtering
- **Stopword filtering**: Portuguese and English (50+ words)
- **KeyBERT scoring**: Semantic relevance using SBERT embeddings
- **TF-IDF scoring**: Statistical importance across documents
- **Combined scoring**: 60% KeyBERT + 40% TF-IDF
- **Parameter filtering**: Removes terms already in search input

### 2. API Integration
- **Endpoint**: `POST /extract-terms`
- **Input**:
  - `enriched_results`: Results from probe search with biblio data
  - `original_params`: Original search parameters (theme, description, etc.)
  - `top_k`: Number of terms to return (default: 20)
- **Output**: List of terms with:
  - Combined score (0-1)
  - KeyBERT score (semantic)
  - TF-IDF score (statistical)
  - Frequency (occurrence count)
  - Sources (title/abstract)

### 3. Pipeline Integration
- **Function**: `pipeline.extract_relevant_terms(enriched_results, original_params, top_k)`
- **Workflow**:
  1. Probe search returns enriched results with biblio data
  2. Term extraction processes title + abstract
  3. Returns ranked terms for LLM query refinement

## Fixes Applied

### KeyBERT Parameter Issue
- Removed unsupported `language="multilingual"` parameter
- Now uses default multilingual model behavior

### TF-IDF Vectorizer
- Changed from char-level n-grams to word-level analysis
- Consistent with n-gram extraction pipeline

### OPS Enrichment Logging
- Fixed NoneType error when biblio data is None
- Used safe chaining: `(r.get("biblio") or {}).get("field")`

## Testing

### Test Files
- `test_term_extraction.py`: Standalone TermExtractor verification
- `test_term_extraction_api.py`: Full workflow testing

### Results Example
Query: "internet" → Returns:
```json
[
  {
    "term": "risk",
    "score": 0.529,
    "keybert_score": 0.214,
    "tf_idf_score": 1.0,
    "frequency": 6,
    "sources": ["abstract"]
  },
  {
    "term": "business",
    "score": 0.457,
    "keybert_score": 0.191,
    "tf_idf_score": 0.857,
    "frequency": 5,
    "sources": ["abstract"]
  }
]
```

## Quality Metrics
- ✓ N-gram extraction: 200+ candidates per result
- ✓ Parameter filtering: Original terms excluded
- ✓ Stopword filtering: Removes 50+ common words
- ✓ Score normalization: All scores in [0, 1] range
- ✓ Frequency tracking: Counts occurrences per term
- ✓ Source attribution: Tracks title vs. abstract origin

## Usage Flow

### 1. Build Probe Query
```bash
POST /probe/query
Body: { "theme": "...", "description": "..." }
```

### 2. Run Probe Search (Auto-Enriched)
```bash
POST /probe/search
Body: { "query": {...}, "api": "ops" }
Response: { "results": [...enriched...] }
```

### 3. Extract Relevant Terms
```bash
POST /extract-terms
Body: {
  "enriched_results": [...from step 2...],
  "original_params": { "theme": "...", "description": "..." },
  "top_k": 15
}
Response: { "terms": [...ranked...] }
```

### 4. LLM Refinement
Terms with scores are passed to LLM for final query building.

## Architecture

```
Patent Search Results
        ↓
   Enrichment (OPS /biblio)
        ↓
   Title + Abstract Extraction
        ↓
   N-gram Extraction + Filtering
        ↓
   ┌─────────┬─────────┐
   ↓         ↓
KeyBERT   TF-IDF
(Semantic)(Statistical)
   ↓         ↓
   └─────────┬─────────┘
        ↓
   Score Combination (60/40)
        ↓
   Parameter Filtering
        ↓
   Ranking & Return
        ↓
   LLM Consumption
```

## Status: ✅ COMPLETE AND TESTED

All components are working correctly. The system is ready for:
- Semantic and statistical term extraction
- LLM-based query refinement
- Multi-round search optimization
- Parameter-aware term filtering
