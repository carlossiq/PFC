# OPS API Integration Fix Summary

## Issues Fixed

### 1. **Date Range Syntax Error** (ops_query_builder.py)
**Problem:** Date range was using comma syntax `"20100101,20261231"` which OPS doesn't accept.

**Solution:** Changed to space syntax `"20100101 20261231"` in `_build_date_cql()` method.

```python
# BEFORE:
return f'pd within "{date_from},{date_to}"'

# AFTER:
return f'pd within "{date_from} {date_to}"'
```

**Location:** `services/query_builders/ops_query_builder.py` line 252

---

### 2. **Invalid Request Parameters** (ops_service.py)
**Problem:** OPSService was sending invalid query parameters:
- `range`: OPS doesn't accept this parameter
- `format`: Should be negotiated via Accept header, not as parameter

Example of WRONG request:
```
GET /published-data/search?q=<CQL>&range=1-10&format=json
```

**Solution:** Remove `range` and `format` from query parameters. Only send `q` parameter.

```python
# BEFORE:
response = await self.async_client.get(
    url,
    params={
        "q": cql_query,
        "range": query.get("range", "1-100"),  # ❌ REMOVED
        "format": query.get("format", "json"),  # ❌ REMOVED
    },
    headers=self._get_headers(),
    timeout=self._TIMEOUT_SECONDS,
)

# AFTER:
response = await self.async_client.get(
    url,
    params={"q": cql_query},  # ✓ Only q parameter
    headers=self._get_headers(),  # ✓ Contains Accept: application/json
    timeout=self._TIMEOUT_SECONDS,
)
```

**Location:** `services/search/ops_service.py` lines 267-281

---

## Final OPS Request Structure

After these fixes, the OPS API request will be correctly formatted:

```
GET https://ops.epo.org/3.2/rest-services/published-data/search?q=<CQL>

Headers:
  Authorization: Bearer <oauth_token>
  Accept: application/json
```

---

## Sample Valid CQL Query

With the test case from requirements:
```cql
(ti=("diagnostic system" OR "computer-aided diagnosis" OR "diagnostic ai")) AND 
(ab=("deep learning" OR "neural networks" OR "medical imaging")) AND 
(pd within "20100101 20261231")
```

This will be sent as:
```
GET https://ops.epo.org/3.2/rest-services/published-data/search?q=(ti=("diagnostic%20system"%20OR%20..."diagnostic%20ai"))%20AND%20(ab=("deep%20learning"%20OR%20...))%20AND%20(pd%20within%20"20100101%2020261231")

Headers:
  Authorization: Bearer <token>
  Accept: application/json
```

---

## Architecture Impact

- **OPSQueryBuilder** continues to return dict: `{"query": "<CQL>", "range": "...", "format": "..."}`
- **OPSService** now correctly extracts only the `query` field and sends it as the `q` parameter
- `range` and `format` fields in the query dict are ignored (harmless backwards compatibility)
- All other APIs (Lens, Scopus) remain unchanged
- Bearer token authentication is preserved
- Accept header is already correctly set to application/json

---

## Why This Fixes the 404 Error

The HTTP 404 was likely caused by OPS API interpreting the invalid `range` and `format` parameters as part of the search identifier, leading to a non-existent endpoint. By removing these invalid parameters and only sending the valid `q` parameter, the request now matches OPS API expectations.

---

## Testing the Fix

The test route at `/api/v1/test/probe-search` should now:
1. Generate valid CQL using the corrected date syntax
2. Construct a proper OPS HTTP request
3. Receive a 200 response (instead of 404)
4. Parse the XML-converted-to-JSON response correctly
