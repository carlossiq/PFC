# OPS API Fix - Testing & Validation Example

## Quick Test Using curl

### Test 1: Medical Diagnostic Patents

```bash
# Request
curl -X POST http://localhost:8000/api/v1/test/probe-search \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "medical diagnostic AI",
    "description": "Patents related to computer-aided diagnosis using artificial intelligence",
    "area_of_study": "medical imaging and diagnostics",
    "keywords": ["diagnostic", "AI", "medical imaging", "deep learning"]
  }'
```

**Expected Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "run_id": "abc123...",
    "llm_strategy": {
      "active_fields": {...},
      "title": {...},
      "abstract": {...}
    },
    "query_generated": {
      "api": "ops",
      "search_mode": "probe",
      "cql_query": "(ti=(...)) AND (ab=(...)) AND (pd within \"20100101 20261231\")",
      "full_query": {...}
    },
    "api_results": {
      "api": "ops",
      "success": true,
      "total_available": 42,
      "results_returned": 10,
      "duration_seconds": 2.34
    },
    "documents": {
      "total_retrieved": 10,
      "samples": [...]
    }
  },
  "message": "Probe search completed: 10 documents found"
}
```

---

### Test 2: Solar Energy Patents

```bash
# Request
curl -X POST http://localhost:8000/api/v1/test/probe-search \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "solar energy technology",
    "description": "Patents related to photovoltaic systems and solar panel efficiency improvements",
    "area_of_study": "renewable energy and photovoltaics",
    "keywords": ["solar", "photovoltaic", "PV", "efficiency"]
  }'
```

**Expected Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "run_id": "def456...",
    "query_generated": {
      "cql_query": "(ti=(...solar...)) AND (pd within \"20100101 20261231\")",
      ...
    },
    "api_results": {
      "api": "ops",
      "success": true,
      "total_available": 1856,
      "results_returned": 10,
      "duration_seconds": 1.67
    },
    ...
  }
}
```

---

## Sample CQL Queries Generated

### Query 1: Medical AI
```cql
(ti=(("diagnostic" OR "diagnosis") AND ("artificial intelligence" OR "deep learning" OR "neural network"))) 
AND 
(ab=(("medical imaging" OR "image analysis" OR "computer aided") AND ("machine learning" OR "AI"))) 
AND 
(pd within "20100101 20261231")
```

### Query 2: Solar Energy
```cql
(ti=("solar" OR "photovoltaic" OR "PV" OR "solar panel")) 
AND 
(ab=("efficiency" OR "conversion" OR "optimization")) 
AND 
(pd within "20100101 20261231")
```

### Key Validation Points ✓
- Date range uses **SPACE** not comma: `"20100101 20261231"` ✓
- Each clause wrapped in parentheses: `(ti=(...)) AND (...)`
- CQL operators: `OR` within terms, `AND` between fields
- Field abbreviations from OPS: `ti` (title), `ab` (abstract), `pd` (publication date)

---

## HTTP Request Trace (What Gets Sent to OPS)

### Actual HTTP Request Built
```
GET https://ops.epo.org/3.2/rest-services/published-data/search?q=%28ti%3D%28%28%22diagnostic%22%20OR%20%22diagnosis%22%29%20AND%20%28%22AI%22%20OR%20%22machine%20learning%22%29%29%29%20AND%20%28ab%3D...%29%20AND%20%28pd%20within%20%2220100101%2020261231%22%29

Headers:
  Authorization: Bearer [OAUTH_TOKEN]
  Accept: application/json
  User-Agent: httpx/...
```

### What OPS Receives
1. **Endpoint:** `/published-data/search` ✓
2. **Parameter:** `q=[CQL query]` ✓
3. **Auth:** Bearer token ✓
4. **Format Request:** Accept header ✓
5. **Invalid Parameters:** None ✓

### Response from OPS (200 OK)
```json
{
  "ops:world-patent-data": {
    "ops:biblio-search": {
      "@total-result-count": "42",
      "ops:search-result": [
        {
          "@sequence": "1",
          "@id": "patent1",
          "ops:biblio": {...}
        },
        ...
      ]
    }
  }
}
```

---

## Validation Steps

### Step 1: Verify CQL Generation
```bash
# Call the LLM debug route to see generated CQL
curl -X POST http://localhost:8000/api/v1/test/llm-enriched \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "solar energy",
    "description": "photovoltaic technology",
    "area_of_study": "renewable energy",
    "keywords": ["solar"]
  }'
```

Look for:
- ✓ `pd within "20100101 20261231"` (with SPACE, not comma)
- ✓ Valid CQL syntax with proper operators
- ✓ Field abbreviations: `ti`, `ab`, `cpc`, `ipc`, `pa`, `in`

### Step 2: Verify Query Building
```bash
# Check what query dict is built for OPS
# The response will show query_generated.cql_query
```

Verify:
- ✓ Only `q` parameter in final request
- ✓ No `range` or `format` parameters
- ✓ Date syntax correct

### Step 3: Verify OPS Response
```bash
# Monitor HTTP status from /api/v1/test/probe-search
```

Verify:
- ✓ Status 200 (not 404)
- ✓ `success: true` in api_results
- ✓ `results_returned > 0`
- ✓ `duration_seconds` reasonable (1-10 seconds)

---

## Common Issues & Solutions

### Issue: Still Getting 404
**Cause:** Code not reloaded or cache issue  
**Solution:**
```bash
# Restart the server
pkill -f uvicorn
sleep 2
cd /path/to/project
python -m uvicorn main:app --reload
```

### Issue: CQL Query Has Comma in Date
**Cause:** Code changes not applied  
**Solution:**
```bash
git log --oneline -5  # Verify commit 0cb6ef6 is present
git diff HEAD~1..HEAD services/query_builders/ops_query_builder.py  # Check date syntax
```

### Issue: Getting 'NoneType' or Parse Errors
**Cause:** OPS response format unexpected  
**Solution:**
- Check if OPS returned XML instead of JSON
- Verify Accept header is "application/json"
- Check OPS service token is valid

---

## Expected Behavior After Fix

| Scenario | BEFORE | AFTER |
|----------|--------|-------|
| HTTP Status | 404 Not Found | 200 OK ✓ |
| Error Message | "endpoint not found" | (success=true) ✓ |
| Date Query | Error parsing | Works ✓ |
| Results Returned | 0 (error) | N > 0 ✓ |
| Response Time | N/A | 1-5 seconds ✓ |

---

## Troubleshooting Logs

### What to Look For in Logs
```
[SUCCESS]
ops_token_obtained - token is valid
ops_search_attempt - attempt=1
ops_search_success - results_count=10, total_count=42, duration=2.34

[ERROR - Still Broken]
ops_search_http_error - status_code=404
ops_search_error - "'str' object has no attribute 'get'"
```

### Enable Debug Logging
```python
# In your .env or config
LOG_LEVEL=DEBUG

# Then search for "ops_" in logs
```

---

## Final Checklist

- [ ] Code changes are applied (git log shows commit 0cb6ef6)
- [ ] Server is restarted (new code loaded)
- [ ] CQL date uses space: `"20100101 20261231"` ✓
- [ ] HTTP request has only `q` parameter ✓
- [ ] Accept header is "application/json" ✓
- [ ] Bearer token is included ✓
- [ ] OPS returns HTTP 200 ✓
- [ ] Results are returned (not empty) ✓
- [ ] No 404 errors ✓
- [ ] No parsing errors ✓

Once all items are checked, the OPS API integration is working correctly!
