# Complete Research Prospecting Workflow

## Overview

The complete research prospecting workflow integrates:
- LLM-based topic refinement and query generation
- Multi-API search (OPS, Scopus, Lens)
- Semantic term extraction
- Results persistence to PostgreSQL
- Phase timing and metrics tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React/Vue)                         │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│              FastAPI Routes (/chat/*)                        │
│  - /refine-topic                                             │
│  - /probe/query, /probe/search                               │
│  - /extract-terms                                            │
│  - /final/queries-multi, /final/search                       │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│         ResearchWorkflow (Coordinator)                       │
│  - Manages research lifecycle                                │
│  - Coordinates pipeline calls                                │
│  - Persists data at each stage                               │
└──────────────┬──────────────────────────────────────────────┘
               │
     ┌─────────┴──────────┬──────────────┬──────────────┐
     │                    │              │              │
┌────▼────┐    ┌─────────▼──┐  ┌───────▼──┐   ┌──────▼──┐
│ Pipeline │    │Research    │  │ API      │   │ Database │
│ Functions│    │Service     │  │ Services │   │ Session  │
└────────┘    │ (ORM)       │  │(OPS,Scop)│   └──────────┘
              └────────────┘  └──────────┘
```

## Database Schema

Five main tables store complete research workflow:

### 1. Research (Main Container)
- UUID research ID
- Title, description, user input
- All 3 query variants (specific, balanced, generic)
- Chosen variant
- Result counts (patents, articles)
- LaTeX content
- Timing data (as JSON dict)
- Created/updated timestamps

### 2. ResearchPatentDocument (Results)
- Foreign key to Research
- Publication number, source, title, abstract
- Applicants, inventors, IPC/CPC codes
- Filing/publication/grant dates
- Legal status, relevance score
- Query variant that found it

### 3. ResearchScholarlyDocument (Results)
- Foreign key to Research
- DOI, source, title, abstract
- Authors, affiliations, journal
- Volume, issue, pages, publication date
- Keywords, field of study, citations
- Relevance score, query variant

### 4. ResearchMetrics (Aggregated Data)
- Patent counts by year, applicant, classification, legal status
- Article counts by year, journal, field, citations
- Top entities (applicants, inventors, authors, journals)
- Growth trends and variant comparisons
- Patent vs article ratio

### 5. ResearchPhase (Timing)
- Phase name (refine_topic, probe_search, term_extraction, final_query_generation, final_search)
- Started/completed timestamps
- Duration in seconds
- Status (completed, failed, skipped)
- Error message if failed

## Complete Workflow Example

### Step 1: Initialize Database
```bash
# Run once to create tables
python -m db.init_db

# Or tables are auto-created on app startup
uvicorn app.main:app --reload
```

### Step 2: Backend Implementation (Python)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from services.research_workflow import ResearchWorkflow
from db.session import db_session

async def complete_workflow_example():
    """Demonstra o fluxo completo com persistência de dados."""
    
    # Obter sessão
    async with db_session.async_session_maker() as session:
        # Inicializar workflow
        workflow = ResearchWorkflow(session)
        
        # Etapa 1: Criar pesquisa
        research = await workflow.start_research(
            title="E-commerce Technology Prospecting 2024",
            description="Identify emerging technologies in online retail"
        )
        print(f"[OK] Research created: {research.research_id}")
        
        # Etapa 2: Refinar tema
        refined = await workflow.refine_topic(
            theme="e-commerce",
            description="online retail technologies",
            area_of_study="Information Technology"
        )
        print(f"[OK] Topic refined: {len(refined['candidates'])} candidates")
        
        # Etapa 3: Busca exploratória
        probe_results = await workflow.build_and_execute_probe_search(
            intake=InputIntake(
                theme=refined['candidates'][0]['theme'],
                description=refined['candidates'][0]['description'],
                area_of_study=refined['candidates'][0]['area_of_study']
            ),
            api="ops"
        )
        print(f"[OK] Probe search: {probe_results['results_count']} results")
        
        # Etapa 4: Extração de termos
        terms = await workflow.extract_terms(
            enriched_results=probe_results['results'],
            original_params={
                'theme': refined['candidates'][0]['theme'],
                'description': refined['candidates'][0]['description']
            },
            top_k=20
        )
        print(f"[OK] Terms extracted: {len(terms['terms'])} terms")
        
        # Etapa 5: Gerar 3 variações de query
        queries = await workflow.build_final_queries(
            intake=InputIntake(
                theme=refined['candidates'][0]['theme'],
                description=refined['candidates'][0]['description']
            ),
            extracted_terms=terms['terms'],
            api="ops"
        )
        print(f"[OK] Queries generated: 3 variants")
        
        # Etapa 6: Executar busca final
        final_results = await workflow.execute_final_search(
            query=queries['queries']['balanced']['query'],
            api="ops",
            query_variant="balanced",
            max_results=500
        )
        print(f"[OK] Final search: {final_results['results_count']} results")
        
        # Confirmar transação
        await session.commit()
        print(f"[OK] All data persisted to database")
        
        # Recuperar pesquisa completa
        research = await session.get(Research, research.id)
        print(f"""
        ===== WORKFLOW COMPLETED =====
        Research ID: {research.research_id}
        Patents found: {research.patent_results_count}
        Articles found: {research.scholarly_results_count}
        Total results: {research.total_results_count}
        Status: {research.status}
        ============================
        """)
```

### Step 3: Frontend Integration

#### React Hook to Track Research Progress
```typescript
import { useState, useEffect } from 'react';

interface ResearchState {
  researchId?: string;
  step: 'initial' | 'refining' | 'probing' | 'extracting' | 'generating' | 'searching' | 'complete';
  candidateCount?: number;
  probeResultsCount?: number;
  termsCount?: number;
  finalResultsCount?: number;
  timing?: Record<string, number>;
}

export function useResearchWorkflow() {
  const [state, setState] = useState<ResearchState>({ step: 'initial' });

  const runCompleteWorkflow = async (theme: string) => {
    try {
      // Step 1: Refine topic
      setState(prev => ({ ...prev, step: 'refining' }));
      const refined = await fetch('/api/chat/refine-topic', {
        method: 'POST',
        body: JSON.stringify({ theme })
      }).then(r => r.json());
      
      setState(prev => ({
        ...prev,
        candidateCount: refined.data.candidates.length,
        step: 'probing'
      }));

      // Step 2: Probe search
      const probe = await fetch('/api/chat/probe/search', {
        method: 'POST',
        body: JSON.stringify({
          query: /* ... */,
          api: 'ops'
        })
      }).then(r => r.json());
      
      setState(prev => ({
        ...prev,
        probeResultsCount: probe.data.results_count,
        step: 'extracting'
      }));

      // Step 3: Extract terms
      const terms = await fetch('/api/chat/extract-terms', {
        method: 'POST',
        body: JSON.stringify({
          enriched_results: probe.data.results,
          original_params: { theme }
        })
      }).then(r => r.json());
      
      setState(prev => ({
        ...prev,
        termsCount: terms.data.count,
        step: 'generating'
      }));

      // Step 4: Generate queries
      const queries = await fetch('/api/chat/final/queries-multi', {
        method: 'POST',
        body: JSON.stringify({
          intake: { theme },
          extracted_terms: terms.data.terms
        })
      }).then(r => r.json());
      
      setState(prev => ({ ...prev, step: 'searching' }));

      // Step 5: Execute final search
      const final = await fetch('/api/chat/final/search', {
        method: 'POST',
        body: JSON.stringify({
          query: queries.data.queries.balanced.query,
          api: 'ops'
        })
      }).then(r => r.json());
      
      setState(prev => ({
        ...prev,
        finalResultsCount: final.data.results_count,
        step: 'complete'
      }));

    } catch (error) {
      console.error('Workflow error:', error);
    }
  };

  return { state, runCompleteWorkflow };
}
```

## Data Persistence Points

Each step automatically persists:

| Step | Function | Persists |
|------|----------|----------|
| Refine Topic | `RefiningService.refine_topic()` | User input, refined candidates |
| Build Probe Query | `OPSQueryBuilder.build_query()` | Probe query, API choice |
| Run Probe Search | `OPSService.search()` | (Results not persisted at this stage) |
| Extract Terms | `TermExtractionService.extract()` | Extracted terms with scores |
| Build Final Queries | `QueryBuilder.build_final_queries()` | 3 query variants, complexity scores |
| Execute Final Search | `OPSService.search()` | Patent/article documents, relevance scores |

## Retrieving Results

### Get Complete Research
```python
async with db_session.async_session_maker() as session:
    research = await session.get(Research, research_id)
    print(f"Title: {research.title}")
    print(f"Patents: {research.patent_results_count}")
    print(f"Articles: {research.scholarly_results_count}")
    print(f"Timing: {research.timing}")  # Dict with phase durations
```

### Get Patent Results
```python
from sqlalchemy import select

async with db_session.async_session_maker() as session:
    stmt = select(ResearchPatentDocument).where(
        ResearchPatentDocument.research_id == research_id
    )
    result = await session.execute(stmt)
    patents = result.scalars().all()
    
    for patent in patents:
        print(f"{patent.publication_number}: {patent.title}")
        print(f"  Applicants: {patent.applicants}")
        print(f"  Relevance: {patent.relevance_score}")
```

### Get Metrics
```python
research = await session.get(Research, research_id)
metrics = research.metrics

print(f"Patents by year: {metrics.patent_by_year}")
print(f"Articles by journal: {metrics.article_by_journal}")
print(f"Top applicants: {metrics.top_patent_applicants}")
```

## Configuration

Required environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/prospecting

# API Keys (existing)
OPS_USERNAME=...
OPS_PASSWORD=...
SCOPUS_API_KEY=...
LENS_API_TOKEN=...

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=...

# Query Settings
PROBE_TOP_K=10
FINAL_TOP_K=500
LLM_MAX_QUERY_COMPLEXITY=60
```

## Next Steps

1. ✅ Database schema created
2. ✅ ResearchService CRUD operations
3. ✅ ResearchWorkflow coordination layer
4. ✅ Database initialization script
5. ⏳ Metrics aggregation and calculation
6. ⏳ LaTeX report generation
7. ⏳ API endpoints for accessing persisted data
8. ⏳ Frontend integration with research ID tracking

## Performance Considerations

- Database indexes on research_id, created_at, query_variant
- Async session pooling in production (pool_size=20-50)
- Lazy loading of related documents (use selectinload for eager load)
- Metrics table updated after final search completes
- Timing data stored as JSON dict in main research record
