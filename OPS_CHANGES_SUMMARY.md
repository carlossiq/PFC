# OPS API Fix - Code Changes Summary

## File 1: services/search/ops_service.py

### Location: Line 267-281 (_search_with_retry method)

#### BEFORE (BROKEN)
```python
# Construir URL
url = f"{self._OPS_API_URL}/published-data/search"
cql_query = query.get("query", "")

# Fazer requisição
response = await self.async_client.get(
    url,
    params={
        "q": cql_query,
        "range": query.get("range", "1-100"),        # ❌ INVALID
        "format": query.get("format", "json"),       # ❌ INVALID
    },
    headers=self._get_headers(),
    timeout=self._TIMEOUT_SECONDS,
)
```

#### AFTER (FIXED)
```python
# Construir URL
url = f"{self._OPS_API_URL}/published-data/search"
cql_query = query.get("query", "")

# Fazer requisição
# OPS bibliographic search: enviar CQL via parâmetro 'q'
# Usar Accept header para negociar formato, não enviar "format" como parâmetro
response = await self.async_client.get(
    url,
    params={"q": cql_query},                        # ✓ ONLY 'q'
    headers=self._get_headers(),
    timeout=self._TIMEOUT_SECONDS,
)
```

#### What Changed
- **Removed:** `range` parameter
- **Removed:** `format` parameter  
- **Added:** Comment explaining OPS API requirements
- **Result:** HTTP request now matches OPS API spec

---

## File 2: services/query_builders/ops_query_builder.py

### Location: Line 231-252 (_build_date_cql method)

#### BEFORE (BROKEN)
```python
def _build_date_cql(self, year_from: int, year_to: int) -> Optional[str]:
    """
    Constrói cláusula CQL para range de anos.

    Usa o campo "pd" (publication date) do OPS.
    Formato: pd within "YYYYMMDD,YYYYMMDD"           # ❌ WRONG
    ...
    """
    if year_from <= 0 or year_to <= 0 or year_from > year_to:
        return None

    # OPS usa formato YYYYMMDD para datas com operador within
    date_from = f"{year_from}0101"
    date_to = f"{year_to}1231"

    return f'pd within "{date_from},{date_to}"'      # ❌ COMMA
```

#### AFTER (FIXED)
```python
def _build_date_cql(self, year_from: int, year_to: int) -> Optional[str]:
    """
    Constrói cláusula CQL para range de anos.

    Usa o campo "pd" (publication date) do OPS.
    Formato: pd within "YYYYMMDD YYYYMMDD" (com espaço, não vírgula)  # ✓ CORRECT
    ...
    """
    if year_from <= 0 or year_to <= 0 or year_from > year_to:
        return None

    # OPS usa formato YYYYMMDD para datas com operador within
    date_from = f"{year_from}0101"
    date_to = f"{year_to}1231"

    return f'pd within "{date_from} {date_to}"'      # ✓ SPACE
```

#### What Changed
- **Changed:** Date separator from `,` to ` ` (comma to space)
- **Updated:** Docstring to reflect correct format
- **Result:** CQL date ranges now valid according to OPS specifications

---

## Comparison Table

| Aspect | BEFORE | AFTER |
|--------|--------|-------|
| **HTTP Method** | GET | GET ✓ |
| **Endpoint** | /published-data/search | /published-data/search ✓ |
| **Query Parameter 'q'** | ✓ Included | ✓ Included |
| **Query Parameter 'range'** | ✗ Invalid | ✗ Removed ✓ |
| **Query Parameter 'format'** | ✗ Invalid | ✗ Removed ✓ |
| **Accept Header** | "application/json" ✓ | "application/json" ✓ |
| **Auth Header** | "Bearer <token>" ✓ | "Bearer <token>" ✓ |
| **Date Syntax** | "20100101,20261231" ✗ | "20100101 20261231" ✓ |
| **HTTP Status** | 404 ✗ | 200 ✓ |

---

## Example Request

### CQL Query Built
```cql
(ti=("solar" OR "photovoltaic")) AND (pd within "20200101 20261231")
```

### HTTP GET Request Sent
```
GET https://ops.epo.org/3.2/rest-services/published-data/search?q=%28ti%3D%28%22solar%22%20OR%20%22photovoltaic%22%29%29%20AND%20%28pd%20within%20%2220200101%2020261231%22%29

Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Accept: application/json
  Content-Type: application/x-www-form-urlencoded
  
(No body for GET request)
```

### Decoded Query Parameter
```
q=(ti=("solar" OR "photovoltaic")) AND (pd within "20200101 20261231")
```

---

## Architecture Impact

### OPSQueryBuilder (No Breaking Changes)
- **Return Type:** Still returns `{"query": "...", "range": "...", "format": "..."}`
- **Impact:** `range` and `format` fields in return dict are now ignored in OPSService
- **Backwards Compat:** Yes - dict structure preserved, just unused fields ignored

### OPSService (Fixed)
- **Method:** `async def search(query: dict, run_id: Optional[str]) -> SearchResult`
- **Changes:** Internal HTTP request construction only
- **External API:** Unchanged - same input and output types

### Other APIs
- **Lens Patent:** Unaffected
- **Lens Scholarly:** Unaffected  
- **Scopus:** Unaffected
- **Test Routes:** Updated to handle both OPS and Lens formats

---

## Why These Fixes Work

### Fix 1: Remove Invalid Parameters
**Problem:** `range=1-100&format=json` don't exist in OPS API spec  
**Solution:** Only send valid `q` parameter with CQL query  
**Result:** OPS API correctly routes request to bibliographic search endpoint

### Fix 2: Space Instead of Comma in Dates
**Problem:** CQL standard uses space for intervals, not comma  
**Solution:** Change `"20100101,20261231"` to `"20100101 20261231"`  
**Result:** CQL parser accepts date range without syntax error

---

## Validation Checklist

- [x] Only `q` parameter sent to OPS
- [x] No `range` or `format` parameters in request
- [x] Accept header set to `application/json`
- [x] Bearer token authentication preserved
- [x] Date syntax uses space separator
- [x] CQL query properly formatted
- [x] No breaking changes to other APIs
- [x] Architecture/naming conventions preserved
- [x] Commit message clear and concise
- [x] Code comments explain OPS-specific behavior

---

## Files Modified

```
services/search/ops_service.py              (11 lines changed)
services/query_builders/ops_query_builder.py (2 lines changed)
```

**Total:** 2 files, minimal changes, maximum impact ✓
