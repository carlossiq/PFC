# Final Query Generation with Extracted Terms

## Overview
Sistema completo para gerar 3 variações de queries finais usando parâmetros originais e termos extraídos, com diferentes níveis de especificidade (specific, balanced, generic).

## Architecture

```
Original Parameters + Extracted Terms (with scores)
                    ↓
         LLM Generation (3 variants)
                    ↓
    ┌───────────┬─────────────┬──────────┐
    ↓           ↓             ↓
 SPECIFIC    BALANCED      GENERIC
(high pre-  (balanced   (high recall)
 cision)    coverage)
    ↓           ↓             ↓
Complexity  Complexity   Complexity
 Validation  Validation   Validation
    ↓           ↓             ↓
 Query with   Query with    Query with
  metadata     metadata      metadata
    ↓           ↓             ↓
 └───────────┬─────────────┬──────────┘
              ↓
        Return 3 Queries
              ↓
      Final Search on API
```

## Components

### 1. Function: `build_final_queries_with_extraction()`

**Location**: `services/tools/pipeline.py`

**Signature**:
```python
async def build_final_queries_with_extraction(
    intake: InputIntake,
    extracted_terms: list[dict[str, Any]],
    api: str = "ops",
) -> dict[str, Any]
```

**Input**:
- `intake`: Original search parameters (theme, description, area_of_study, keywords)
- `extracted_terms`: Terms from `/extract-terms` with scores, frequency, sources
- `api`: Target API (ops, scopus, lens_patent, lens_scholarly)

**Process**:
1. Load final_system_prompt.md
2. Prepare user message with all parameters and terms
3. Filter terms by score thresholds:
   - Specific: score > 0.4 (2+ terms typically)
   - Balanced: score > 0.3 (3+ terms typically)
   - Generic: score > 0.2 (5+ terms typically)
4. Call LLM with `call_raw_json()` for JSON generation
5. Validate complexity of each query variant
6. Return all 3 with metadata

**Output**:
```python
{
    "success": bool,
    "api": str,
    "user_input": dict,
    "extracted_terms_summary": {
        "total": int,
        "high_score": int,      # score > 0.4
        "mid_score": int,       # 0.3 < score <= 0.4
        "all_score": int        # score > 0.2
    },
    "queries": {
        "specific": {
            "success": bool,
            "query": {
                "query": str,        # CQL/Boolean query
                "range": str,        # "1-100"
                "format": str        # "json"
            },
            "rationale": str,
            "expected_precision": str,  # "high"
            "focus_areas": [str],   # Top terms used
            "complexity": {
                "score": float,      # 0-100
                "level": str,        # "simple", "moderate", "complex"
                "passed": bool,      # < limit?
                "warnings": [str]
            }
        },
        "balanced": {...},   # Same structure
        "generic": {...}     # Same structure
    }
}
```

### 2. System Prompt: `final_system_prompt.md`

**Purpose**: Guide LLM to generate 3 query variations with:
- Different specificity levels
- Proper term grouping (OR for synonyms)
- Minimal AND operators
- Focus on ABSTRACT OR TITLE
- Score-aware term selection
- API-specific syntax

**Key Features**:
- Explains score thresholds for each variant
- Provides query structure guidelines
- API-specific optimization tips (OPS, Scopus, USPTO)
- Complexity management strategies
- Success criteria for LLM output

### 3. API Endpoint: `POST /final/queries-multi`

**Location**: `api/routes/chat.py`

**Request**:
```json
{
    "intake": {
        "theme": "...",
        "description": "...",
        "area_of_study": null,
        "keywords": null
    },
    "extracted_terms": [
        {
            "term": "risk",
            "score": 0.529,
            "keybert_score": 0.214,
            "tf_idf_score": 1.0,
            "frequency": 6,
            "sources": ["abstract"]
        },
        ...
    ],
    "api": "ops"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "api": "ops",
        "queries": {
            "specific": {
                "success": true,
                "query": {"query": "...", "range": "1-100", "format": "json"},
                "complexity": {
                    "score": 16.64,
                    "level": "simple",
                    "passed": true
                },
                "rationale": "Combines original parameters with highest-scoring extracted terms...",
                "expected_precision": "high",
                "focus_areas": ["risk", "business"]
            },
            "balanced": {...},
            "generic": {...}
        }
    }
}
```

## Query Characteristics

### SPECIFIC Variant
- **Score Threshold**: > 0.4
- **Expected Terms**: 2-3 high-scoring terms
- **AND Operators**: Max 3
- **Purpose**: Highest precision, narrowest scope
- **Use Case**: When you want only the most relevant documents
- **Example**: `(ti = ("risk" OR "business")) AND (ab = "investment")`

### BALANCED Variant (RECOMMENDED)
- **Score Threshold**: > 0.3
- **Expected Terms**: 3-5 mid-range terms
- **AND Operators**: 1-2
- **Purpose**: Balance between recall and precision
- **Use Case**: Default choice for most searches
- **Example**: `(ti OR ab = (("risk" OR "business") AND ("investment" OR "capital")))`

### GENERIC Variant
- **Score Threshold**: > 0.2
- **Expected Terms**: 5+ all available terms
- **AND Operators**: 0-1
- **Purpose**: Highest recall, broadest scope
- **Use Case**: Exploratory searches, finding all related documents
- **Example**: `(ti OR ab = ("risk" OR "business" OR "investment" OR "market" OR "capital"))`

## Workflow

### Step 1: Probe Search with Enrichment
```bash
POST /probe/search
{
    "query": {...},
    "api": "ops"
}
→ Returns enriched results with biblio data
```

### Step 2: Term Extraction
```bash
POST /extract-terms
{
    "enriched_results": [...from step 1...],
    "original_params": {"theme": "...", "description": "..."},
    "top_k": 15
}
→ Returns 15 ranked terms with scores
```

### Step 3: Generate Final Queries
```bash
POST /final/queries-multi
{
    "intake": {"theme": "...", "description": "..."},
    "extracted_terms": [...from step 2...],
    "api": "ops"
}
→ Returns 3 queries with different specificity
```

### Step 4: Run Final Search (Choose One)
```bash
POST /final/search  # Not yet implemented
{
    "query": {...from specific/balanced/generic...},
    "api": "ops"
}
→ Returns comprehensive results (up to final_top_k)
```

## Complexity Validation

Each query variant is validated against the complexity limit:
- **Default Maximum**: `llm_max_query_complexity = 0.6` (score 60/100)
- **Specific**: Usually ~16-25 (simple)
- **Balanced**: Usually ~20-35 (simple to moderate)
- **Generic**: Usually ~30-45 (moderate)

If complexity exceeds limit:
- Still returned in response
- Marked as `"passed": false`
- Warning included in response
- User can still use but should be aware

## Term Scoring Strategy

### Score Thresholds (from TermExtractor)
- Combined Score = 60% KeyBERT + 40% TF-IDF
- High Score (specific): score > 0.4
  - Both semantic AND statistical relevance
  - Primary concept indicators
  
- Mid Score (balanced): 0.3 < score ≤ 0.4
  - Good semantic or statistical relevance
  - Related concepts
  
- Low Score (generic): 0.2 < score ≤ 0.3
  - Moderate relevance
  - Contextual/supporting concepts
  
- Excluded: score ≤ 0.2
  - Low signal, might dilute search

## API-Specific Optimizations

### OPS (Patents)
- **Format**: CQL
- **Fields**: `ti` (title), `ab` (abstract), `claims`, `pa` (applicant), `ipc`, `cpc`
- **Date**: `pd within "YYYYMMDD YYYYMMDD"`
- **Focus**: Abstract and title are less detailed than academic papers
- **Operators**: `AND`, `OR`, `NOT`

### Scopus (Academic)
- **Format**: Boolean
- **Fields**: `TITLE`, `ABSTRACT`, `KEYWORDS`
- **Date**: `PUBDATE [date range]`
- **Focus**: Rich abstract text available
- **Operators**: `AND`, `OR`, `NOT`

### Lens Patents/Scholarly
- **Format**: Boolean
- **Fields**: Varies by type
- **Flexible**: Supports various search syntaxes

## Example Usage

### Input
```python
intake = InputIntake(
    theme="internet technology",
    description="e-commerce systems"
)

extracted_terms = [
    {"term": "risk", "score": 0.529, "frequency": 6},
    {"term": "business", "score": 0.457, "frequency": 5},
    {"term": "high", "score": 0.392, "frequency": 6},
    {"term": "capital", "score": 0.219, "frequency": 2},
    {"term": "investment", "score": 0.217, "frequency": 2},
]
```

### Generated Queries

**SPECIFIC** (score > 0.4):
```
(ti = (("risk" OR "business") AND ("internet"))) 
AND 
(ab = (("risk" OR "business") AND ("technology" OR "e-commerce")))
```

**BALANCED** (score > 0.3):
```
(ti OR ab = (("risk" OR "business") AND ("high" OR "technology") AND ("capital")))
AND 
(pd within "20100101 20261231")
```

**GENERIC** (score > 0.2):
```
(ti OR ab = ("risk" OR "business" OR "high" OR "capital" OR "investment"))
AND 
(pd within "20100101 20261231")
```

## Status: ✅ IMPLEMENTED AND TESTED

- ✓ Function implemented and working
- ✓ System prompt created with guidelines
- ✓ API endpoint available
- ✓ Complexity validation working
- ✓ All 3 variants generate successfully
- ✓ Scores properly used for term filtering
- ✓ Ready for final search integration

## Next Steps

1. **Implement `/final/search` endpoint**
   - Run search using selected query variant
   - Return comprehensive results (up to final_top_k)

2. **Multi-turn refinement**
   - User selects which variant performed best
   - Generate new queries based on feedback

3. **Result deduplication**
   - Merge results from multiple query variants
   - Rank by relevance and source

4. **Feedback loop**
   - Track which variants performed best
   - Improve score thresholds over time
