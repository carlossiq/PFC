# OPS Query Builder Verification & Implementation

## Summary

The `OPSQueryBuilder` has been verified as working correctly and the full search pipeline has been enhanced to support OPS queries end-to-end.

## What Was Fixed

### 1. OPS Query Builder Implementation ✅

The `OPSQueryBuilder` correctly:
- Loads field mapping from `schemas_config/ops.fields.json`
- Maps LLM output attributes to OPS CQL field names
- Generates valid CQL queries with proper syntax
- Handles all field types: textual, simple, and date ranges

**Field Mapping:**
```
LLM Field     → OPS CQL Field
TITLE         → ti
ABSTRACT      → ab
APPLICANT     → pa
INVENTOR      → in
YEAR          → pd
IPC           → ipc
CPC           → cpc
CLAIMS        → claims
FULL_TEXT     → ftxt
```

### 2. Query Generation Example

Input (LLMOutput):
```python
title: TextualFieldQuery(
    groups=[
        TermGroup(terms=["machine learning", "deep learning"], operator=OR),
        TermGroup(terms=["healthcare"], operator=OR)
    ],
    group_operator=AND
)
applicant: SimpleFieldQuery(values=["Samsung", "Apple"])
```

Output (CQL):
```
(ti = (("deep learning" OR "machine learning") AND (healthcare))) 
AND 
(pa = (Apple OR Samsung)) 
AND 
(pd within "20200101 20261231")
```

### 3. Pipeline Integration ✅

**Before:** `run_final_search()` only supported Scopus
**After:** Full support for:
- OPS (European Patent Office) ✅
- Scopus ✅
- Lens Patent ✅
- Lens Scholarly ✅

## Verification Tests

### Test 1: Field Map Loading
```python
builder = OPSQueryBuilder()
# field_map correctly loads: {"TITLE": "ti", "ABSTRACT": "ab", ...}
assert builder.field_map.get("TITLE") == "ti"
```

### Test 2: CQL Generation
```python
query = builder.build_query(llm_output, year_from=2020, year_to=2026)
# Returns: {
#     "query": "(ti = (...)) AND (pa = (...)) AND (pd within ...)",
#     "range": "1-10",
#     "format": "json"
# }
```

### Test 3: Pipeline Execution
- Probe search: OPSQueryBuilder queries are built and validated for complexity
- Final search: OPSQueryBuilder queries can now be executed via `run_final_search()`

## Key Features

### 1. CQL Syntax Generation
- **Textual fields** (title, abstract, claims, full_text): Group operators with OR/AND
- **Simple fields** (applicant, inventor, ipc, cpc): Multiple values with OR
- **Date range** (year): Uses `pd within "YYYYMMDD YYYYMMDD"` syntax

### 2. Query Validation
- Complexity scoring to prevent overly complex queries
- Automatic simplification with LLM retries (up to 3 attempts)
- Detailed complexity analysis with term counts and nesting depth

### 3. Error Handling
- Fallback to default field map if JSON file is missing
- Graceful handling of missing fields in LLMOutput
- Comprehensive logging for debugging

## Implementation Details

### File: `services/query_builders/ops_query_builder.py`

Key methods:
- `build_query()` - Main entry point, orchestrates query building
- `_load_field_map()` - Reads ops.fields.json and extracts field_map
- `_build_textual_cql()` - Generates CQL for textual fields
- `_build_simple_cql()` - Generates CQL for simple fields
- `_build_date_cql()` - Generates CQL for date ranges
- `_escape_cql_term()` - Escapes special characters in terms

### File: `services/tools/pipeline.py`

Updated functions:
- `run_final_search()` - Now supports OPS, Scopus, Lens Patent, and Lens Scholarly

## Configuration

### Environment Variables
- `OPS_ENABLED` - Enable OPS API (default: false)
- `SEARCH_YEAR_FROM` - Start year for searches (default: 2015)
- `SEARCH_YEAR_TO` - End year for searches (default: 2026)
- `PROBE_TOP_K` - Results for probe searches (default: 10)
- `FINAL_TOP_K` - Results for final searches (default: 100)
- `LLM_MAX_QUERY_COMPLEXITY` - Max complexity score (default: 0.6)

### Schema File: `schemas_config/ops.fields.json`
```json
{
  "api": "ops",
  "field_map": {
    "TITLE": "ti",
    "ABSTRACT": "ab",
    "YEAR": "pd",
    "APPLICANT": "pa",
    "INVENTOR": "in",
    "CLAIMS": "claims",
    "FULL_TEXT": "ftxt",
    "IPC": "ipc",
    "CPC": "cpc"
  }
}
```

## Usage Example

```python
# 1. Create query builder
builder = QueryBuilderFactory.create("ops", search_mode="probe")

# 2. Build query from LLM output
query = builder.build_query(
    llm_output=normalized_output,
    year_from=2020,
    year_to=2026
)

# 3. Execute via pipeline
result = await pipeline.run_final_search(
    query=query,
    api="ops",
    max_results=500
)
```

## Status

✅ **COMPLETE** - OPSQueryBuilder is fully functional and integrated into the search pipeline.

All verification points from the implementation plan have been confirmed:
1. ✅ Field map correctly loaded from ops.fields.json
2. ✅ CQL queries generated with proper syntax
3. ✅ OPS now appears in final_search without api_failures
4. ✅ Full pipeline integration from query building to search execution
